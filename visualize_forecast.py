import matplotlib

matplotlib.use('Agg')  # IMPORTANTE: Evita que se abran ventanas de GUI
import matplotlib.pyplot as plt
import sqlite3
import pandas as pd
from prophet import Prophet
import matplotlib.dates as mdates
import os

DB_PATH = "gpon_monitoring.db"


def generate_port_graph(port_name):
    """Función que genera el gráfico y devuelve la ruta del archivo .png"""
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT timestamp as ds, downstream, upstream FROM traffic_history WHERE port_id = ? ORDER BY timestamp ASC"
    df = pd.read_sql_query(query, conn, params=(port_name,))
    conn.close()

    if len(df) < 5:
        return None

    df['ds'] = pd.to_datetime(df['ds'])

    # Entrenamiento rápido para el gráfico
    m_down = Prophet(daily_seasonality=True)
    m_down.fit(df[['ds', 'downstream']].rename(columns={'downstream': 'y'}))
    forecast_down = m_down.predict(m_down.make_future_dataframe(periods=96, freq='15min'))

    m_up = Prophet(daily_seasonality=True)
    m_up.fit(df[['ds', 'upstream']].rename(columns={'upstream': 'y'}))
    forecast_up = m_up.predict(m_up.make_future_dataframe(periods=96, freq='15min'))

    # Creación del gráfico
    plt.figure(figsize=(10, 5))
    plt.plot(df['ds'], df['downstream'], color='#1f77b4', label='Real Down', alpha=0.7)
    plt.plot(forecast_down['ds'], forecast_down['yhat'], 'b--', label='Pred Down')
    plt.plot(df['ds'], df['upstream'], color='#2ca02c', label='Real Up', alpha=0.7)
    plt.plot(forecast_up['ds'], forecast_up['yhat'], 'g--', label='Pred Up')

    plt.title(f"Tráfico GPON - Puerto {port_name}")
    plt.legend()
    plt.tight_layout()

    # Guardamos con un nombre único para evitar conflictos
    file_name = f"graph_{port_name.replace('/', '-')}.png"
    plt.savefig(file_name)
    plt.close()  # Liberar memoria
    return file_name


if __name__ == "__main__":
    # Esto permite que el script siga funcionando solo si lo ejecutás manualmente
    res = generate_port_graph("0/8/0")
    if res: print(f"Gráfico generado en {res}")