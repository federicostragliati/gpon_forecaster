import sqlite3
import pandas as pd
from prophet import Prophet
from prophet.serialize import model_to_json
import os
import json

DB_PATH = "gpon_monitoring.db"
CONFIG_PATH = "config.json"


def train_all():
    if not os.path.exists(CONFIG_PATH):
        print("❌ No existe config.json")
        return

    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)

    conn = sqlite3.connect(DB_PATH)

    for olt in config["olts"]:
        olt_name = olt["name"]
        for port in olt["ports"]:
            port_id = port["id"]
            print(f"🧠 Entrenando {olt_name} - Puerto {port_id}...")

            # Traemos la data filtrada por OLT y Puerto
            query = "SELECT timestamp as ds, downstream, upstream FROM traffic_history WHERE olt_name = ? AND port_id = ?"
            df = pd.read_sql_query(query, conn, params=(olt_name, port_id))

            if len(df) < 10:
                print(f"⚠️ Poca data para {olt_name} {port_id}. Saltando...")
                continue

            for mode in ['downstream', 'upstream']:
                m = Prophet(daily_seasonality=True)
                m.fit(df[['ds', mode]].rename(columns={mode: 'y'}))

                # Guardamos con nombre único: model_OLT_PUERTO_mode.json
                file_name = f"model_{olt_name}_{port_id.replace('/', '_')}_{mode}.json"
                with open(file_name, 'w') as f:
                    f.write(model_to_json(m))

            print(f"✅ Modelos guardados para {port_id}")

    conn.close()


if __name__ == "__main__":
    train_all()