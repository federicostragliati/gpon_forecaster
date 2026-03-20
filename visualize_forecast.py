import pandas as pd
from prophet.serialize import model_from_json
import sqlite3
import os
import plotly.graph_objects as go
import plotly.io as pio
import datetime

def generate_interactive_graph(olt_name, port_id):
    safe_port = port_id.replace('/', '_')
    file_down = f"model_{olt_name}_{safe_port}_downstream.json"
    file_up = f"model_{olt_name}_{safe_port}_upstream.json"

    if not os.path.exists(file_down) or not os.path.exists(file_up):
        return None

    # 1. Cargar modelos
    with open(file_down, 'r') as f:
        m_down = model_from_json(f.read())
    with open(file_up, 'r') as f:
        m_up = model_from_json(f.read())

    # 2. PREDECIR (Lógica corregida)
    # Definimos 7 días con puntos cada 15 minutos (7 días * 24 horas * 4 intervalos = 672 puntos)
    future = m_down.make_future_dataframe(periods=7 * 96, freq='15min')
    future['cap'] = 10000 # Techo de 10 Gbps para crecimiento logístico
    f_down = m_down.predict(future)

    # Predicción para Upstream
    future_up = m_up.make_future_dataframe(periods=7 * 96, freq='15min')
    future_up['cap'] = 10000
    f_up = m_up.predict(future_up)

    # 3. Traer data real de la base de datos
    conn = sqlite3.connect("gpon_monitoring.db")
    df_real = pd.read_sql_query(
        "SELECT timestamp as ds, downstream, upstream FROM traffic_history WHERE olt_name = ? AND port_id = ?",
        conn, params=(olt_name, port_id))
    conn.close()
    df_real['ds'] = pd.to_datetime(df_real['ds'])

    # 4. Construir Gráfico Interactivo con Plotly
    fig = go.Figure()

    # --- SERIE DOWNSTREAM ---
    # Área de incertidumbre
    fig.add_trace(go.Scatter(x=f_down['ds'], y=f_down['yhat_upper'], mode='lines', line_color='rgba(0,0,255,0)', showlegend=False))
    fig.add_trace(go.Scatter(x=f_down['ds'], y=f_down['yhat_lower'], fill='tonexty', mode='lines', line_color='rgba(0,0,255,0)', fillcolor='rgba(0,0,255,0.1)', name='Confianza Down'))
    # Datos reales y predicción
    fig.add_trace(go.Scatter(x=df_real['ds'], y=df_real['downstream'], name='Real Downstream', line=dict(color='blue', width=2)))
    fig.add_trace(go.Scatter(x=f_down['ds'], y=f_down['yhat'], name='Predicción Down', line=dict(color='blue', width=2, dash='dash')))

    # --- SERIE UPSTREAM ---
    # Área de incertidumbre
    fig.add_trace(go.Scatter(x=f_up['ds'], y=f_up['yhat_upper'], mode='lines', line_color='rgba(0,255,0,0)', showlegend=False))
    fig.add_trace(go.Scatter(x=f_up['ds'], y=f_up['yhat_lower'], fill='tonexty', mode='lines', line_color='rgba(0,255,0,0)', fillcolor='rgba(0,255,0,0.1)', name='Confianza Up'))
    # Datos reales y predicción
    fig.add_trace(go.Scatter(x=df_real['ds'], y=df_real['upstream'], name='Real Upstream', line=dict(color='green', width=2)))
    fig.add_trace(go.Scatter(x=f_up['ds'], y=f_up['yhat'], name='Predicción Up', line=dict(color='green', width=2, dash='dash')))

    # Configuración de Layout
    fig.update_layout(
        title=f"Forecast Interactivo: {olt_name} - Puerto {port_id}",
        xaxis_title="Tiempo",
        yaxis_title="Mbps",
        template="plotly_white",
        hovermode="x unified"
    )

    # Ajuste manual del eje Y para UpLink de 10G
    fig.update_yaxes(range=[0, 11000], nticks=10, gridcolor='LightGrey')

    # Ajuste del eje X con Zoom inicial (48hs atrás y 7 días adelante)
    hoy = datetime.datetime.now()
    fig.update_xaxes(
        range=[hoy - datetime.timedelta(days=2), hoy + datetime.timedelta(days=7)],
        rangeslider_visible=True
    )

    # Retorno en formato HTML
    return pio.to_html(fig, full_html=False, include_plotlyjs='cdn')