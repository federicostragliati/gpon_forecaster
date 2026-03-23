import pandas as pd
from prophet.serialize import model_from_json
import sqlite3
import os
import json
import plotly.graph_objects as go
import plotly.io as pio
import datetime

CONFIG_PATH = "config.json"


def _load_config():
    """Carga config.json si existe, devuelve dict vacío si no."""
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f_config:
            return json.load(f_config)
    return {}


def generate_interactive_graph(olt_name, port_id):
    safe_port = port_id.replace("/", "_")
    file_down = f"model_{olt_name}_{safe_port}_downstream.json"
    file_up   = f"model_{olt_name}_{safe_port}_upstream.json"

    if not os.path.exists(file_down) or not os.path.exists(file_up):
        return None

    # 1. Cargar configuración para obtener cap y freq consistentes con el entrenamiento
    config = _load_config()
    cap_mbps   = config.get("cap_mbps", 10000)
    polling_sec = config.get("polling_interval", 60)

    # FIX: freq alineada con el polling real en lugar de hardcodear '15min'
    freq = f"{polling_sec}s"
    # FIX: períodos calculados dinámicamente para representar exactamente 7 días
    periods_7d = int(7 * 24 * 3600 / polling_sec)

    # 2. Cargar modelos desde disco
    with open(file_down, "r") as f_model:
        m_down = model_from_json(f_model.read())
    with open(file_up, "r") as f_model:
        m_up = model_from_json(f_model.read())

    # 3. Generar horizonte de predicción (histórico + 7 días futuros)
    GRAPH_FREQ = "15min"
    GRAPH_PERIODS_7D = 7 * 24 * 4  # 672 puntos — liviano para el browser

    future = m_down.make_future_dataframe(periods=GRAPH_PERIODS_7D, freq=GRAPH_FREQ)
    future["cap"] = cap_mbps
    f_down = m_down.predict(future)

    future_up = m_up.make_future_dataframe(periods=GRAPH_PERIODS_7D, freq=GRAPH_FREQ)
    future_up["cap"] = cap_mbps
    f_up = m_up.predict(future_up)

    # 4. Traer datos reales de la base de datos
    # FIX: usar context manager para que la conexión se cierre correctamente
    with sqlite3.connect("gpon_monitoring.db") as conn:
        df_real = pd.read_sql_query(
            "SELECT timestamp as ds, downstream, upstream "
            "FROM traffic_history WHERE olt_name = ? AND port_id = ?",
            conn,
            params=(olt_name, port_id),
        )

    df_real["ds"] = pd.to_datetime(df_real["ds"])

    # 5. Construir gráfico interactivo con Plotly
    fig = go.Figure()

    # --- DOWNSTREAM (azul) ---
    # Banda de confianza: traza superior invisible + relleno hacia abajo
    fig.add_trace(go.Scatter(
        x=f_down["ds"], y=f_down["yhat_upper"],
        mode="lines", line_color="rgba(0,0,255,0)", showlegend=False,
    ))
    fig.add_trace(go.Scatter(
        x=f_down["ds"], y=f_down["yhat_lower"],
        fill="tonexty", mode="lines",
        line_color="rgba(0,0,255,0)", fillcolor="rgba(0,0,255,0.1)",
        name="Confianza Down",
    ))
    fig.add_trace(go.Scatter(
        x=df_real["ds"], y=df_real["downstream"],
        name="Real Downstream", line=dict(color="blue", width=2),
    ))
    fig.add_trace(go.Scatter(
        x=f_down["ds"], y=f_down["yhat"],
        name="Predicción Down", line=dict(color="blue", width=2, dash="dash"),
    ))

    # --- UPSTREAM (verde) ---
    fig.add_trace(go.Scatter(
        x=f_up["ds"], y=f_up["yhat_upper"],
        mode="lines", line_color="rgba(0,255,0,0)", showlegend=False,
    ))
    fig.add_trace(go.Scatter(
        x=f_up["ds"], y=f_up["yhat_lower"],
        fill="tonexty", mode="lines",
        line_color="rgba(0,255,0,0)", fillcolor="rgba(0,255,0,0.1)",
        name="Confianza Up",
    ))
    fig.add_trace(go.Scatter(
        x=df_real["ds"], y=df_real["upstream"],
        name="Real Upstream", line=dict(color="green", width=2),
    ))
    fig.add_trace(go.Scatter(
        x=f_up["ds"], y=f_up["yhat"],
        name="Predicción Up", line=dict(color="green", width=2, dash="dash"),
    ))

    # 6. Layout
    fig.update_layout(
        title=f"Forecast Interactivo: {olt_name} - Puerto {port_id}",
        xaxis_title="Tiempo",
        yaxis_title="Mbps",
        template="plotly_white",
        hovermode="x unified",
    )

    # FIX: rango Y también usa cap_mbps del config en lugar de estar hardcodeado
    fig.update_yaxes(range=[0, cap_mbps * 1.1], nticks=10, gridcolor="LightGrey")

    # Zoom inicial: últimas 48hs + 7 días adelante
    hoy = datetime.datetime.now()
    fig.update_xaxes(
        range=[hoy - datetime.timedelta(days=2), hoy + datetime.timedelta(days=7)],
        rangeslider_visible=True,
    )

    return pio.to_html(fig, full_html=False, include_plotlyjs="cdn")
