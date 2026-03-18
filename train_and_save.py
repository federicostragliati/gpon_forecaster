# train_and_save.py
import sqlite3
import pandas as pd
from prophet import Prophet
from prophet.serialize import model_to_json
import os

DB_PATH = "gpon_monitoring.db"
PORTS = ["0/8/0", "0/9/0"]


def train_all():
    if not os.path.exists(DB_PATH):
        print("❌ No existe la DB.")
        return

    conn = sqlite3.connect(DB_PATH)
    for port in PORTS:
        df = pd.read_sql_query("SELECT timestamp as ds, downstream, upstream FROM traffic_history WHERE port_id = ?",
                               conn, params=(port,))

        if len(df) < 10:
            print(f"⚠️ Poca data para {port}. Saltando...")
            continue

        for mode in ['downstream', 'upstream']:
            m = Prophet(daily_seasonality=True)
            m.fit(df[['ds', mode]].rename(columns={mode: 'y'}))

            file_name = f"model_{port.replace('/', '_')}_{mode}.json"
            with open(file_name, 'w') as f:
                f.write(model_to_json(m))
            print(f"✅ Modelo guardado: {file_name}")
    conn.close()


if __name__ == "__main__":
    train_all()