import pandas as pd
from prophet.serialize import model_from_json
import sqlite3
import os
import plotly.graph_objects as go
import plotly.io as pio

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

    # 2. Predecir (3 meses = 90 días)
    future = m_down.make_future_dataframe(periods=90, freq='D')
    f_down = m_down.predict(future)
    f_up = m_up.predict(future)

    # 3. Traer data real
    conn = sqlite3.connect("gpon_monitoring.db")
    df_real = pd.read_sql_query(
        "SELECT timestamp as ds, downstream, upstream FROM traffic_history WHERE olt_name = ? AND port_id = ?",
        conn, params=(olt_name, port_id))
    conn.close()
    df_real['ds'] = pd.to_datetime(df_real['ds'])

    # 4. Construir Gráfico Interactivo con Plotly
    fig = go.Figure()

    # --- DOWNSTREAM ---
    # Área de incertidumbre
    fig.add_trace(go.Scatter(x=f_down['ds'], y=f_down['yhat_upper'], fill=None, mode='lines', line_color='rgba(0,0,255,0)', showlegend=False))
    fig.add_trace(go.Scatter(x=f_down['ds'], y=f_down['yhat_lower'], fill='tonexty', mode='lines', line_color='rgba(0,0,255,0)', fillcolor='rgba(0,0,255,0.1)', name='Confianza Down'))
    # Línea real
    fig.add_trace(go.Scatter(x=df_real['ds'], y=df_real['downstream'], name='Real Downstream', line=dict(color='blue', width=2)))
    # Predicción
    fig.add_trace(go.Scatter(x=f_down['ds'], y=f_down['yhat'], name='Predicción Down', line=dict(color='blue', width=2, dash='dash')))

    # --- UPSTREAM ---
    # Área de incertidumbre
    fig.add_trace(go.Scatter(x=f_up['ds'], y=f_up['yhat_upper'], fill=None, mode='lines', line_color='rgba(0,255,0,0)', showlegend=False))
    fig.add_trace(go.Scatter(x=f_up['ds'], y=f_up['yhat_lower'], fill='tonexty', mode='lines', line_color='rgba(0,255,0,0)', fillcolor='rgba(0,255,0,0.1)', name='Confianza Up'))
    # Línea real
    fig.add_trace(go.Scatter(x=df_real['ds'], y=df_real['upstream'], name='Real Upstream', line=dict(color='green', width=2)))
    # Predicción
    fig.add_trace(go.Scatter(x=f_up['ds'], y=f_up['yhat'], name='Predicción Up', line=dict(color='green', width=2, dash='dash')))

    fig.update_layout(
        title=f"Forecast Interactivo: {olt_name} - Puerto {port_id}",
        xaxis_title="Tiempo",
        yaxis_title="Mbps",
        template="plotly_white",
        hovermode="x unified"
    )

    # Ajuste manual del eje Y (Mbps)
    fig.update_yaxes(
        range=[0, 11000],  # De 0 a 11 Gbps
        nticks=10,
        gridcolor='LightGrey'
    )

    # Ajuste del eje X (Zoom inicial en los últimos 7 días)
    import datetime
    hoy = datetime.datetime.now()
    hace_dos_dias = hoy - datetime.timedelta(days=2)
    proxima_semana = hoy + datetime.timedelta(days=7)

    fig.update_xaxes(
        range=[hace_dos_dias, proxima_semana],  # El gráfico abre mostrando esta ventana
        rangeslider_visible=True  # Agrega una barra abajo para navegar los 3 meses
    )

    # Devolvemos el HTML del gráfico como un string (un div autoejecutable)
    return pio.to_html(fig, full_html=False, include_plotlyjs='cdn')