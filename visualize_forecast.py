import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
from prophet import Prophet
import matplotlib.dates as mdates

# Configuración
DB_PATH = "gpon_monitoring.db"
PORT_NAME = "0/8/0"  # Cambiá al puerto que quieras graficar
FORECAST_DAYS = 1


def get_data_and_plot():
    # 1. Extraer datos de SQLite
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT timestamp as ds, downstream, upstream FROM traffic_history WHERE port_id = ? ORDER BY timestamp ASC"
    df = pd.read_sql_query(query, conn, params=(PORT_NAME,))
    conn.close()

    if len(df) < 5:
        print("⚠️ Muy poca data en la DB. ¡Dejá correr el poll_worker un rato más!")
        return

    # Convertir 'ds' a datetime por las dudas
    df['ds'] = pd.to_datetime(df['ds'])

    # 2. ENTRENAMIENTO (Necesitamos dos modelos)
    # Modelo Downstream
    m_down = Prophet(daily_seasonality=True)
    m_down.fit(df[['ds', 'downstream']].rename(columns={'downstream': 'y'}))
    forecast_down = m_down.predict(m_down.make_future_dataframe(periods=96, freq='15min'))

    # Modelo Upstream
    m_up = Prophet(daily_seasonality=True)
    m_up.fit(df[['ds', 'upstream']].rename(columns={'upstream': 'y'}))
    forecast_up = m_up.predict(m_up.make_future_dataframe(periods=96, freq='15min'))

    # 3. GRÁFICO DUAL
    plt.figure(figsize=(12, 7))

    # --- Plot Downstream ---
    plt.plot(df['ds'], df['downstream'], color='#1f77b4', label='Real Download (Mbps)', alpha=0.8)
    plt.plot(forecast_down['ds'], forecast_down['yhat'], color='blue', linestyle='--', label='Predicción Down')
    plt.fill_between(forecast_down['ds'], forecast_down['yhat_lower'], forecast_down['yhat_upper'], color='blue',
                     alpha=0.1)

    # --- Plot Upstream ---
    plt.plot(df['ds'], df['upstream'], color='#2ca02c', label='Real Upload (Mbps)', alpha=0.8)
    plt.plot(forecast_up['ds'], forecast_up['yhat'], color='green', linestyle='--', label='Predicción Up')
    plt.fill_between(forecast_up['ds'], forecast_up['yhat_lower'], forecast_up['yhat_upper'], color='green', alpha=0.1)

    # Estética de ingeniería
    plt.title(f"Análisis de Tráfico GPON - Puerto {PORT_NAME}", fontsize=14)
    plt.ylabel("Mbps")
    plt.legend(loc='upper left')
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.tight_layout()

    plt.show()

if __name__ == "__main__":
    get_data_and_plot()