import sqlite3
import pandas as pd
from prophet import Prophet
from prophet.serialize import model_to_json
import os
import json
import logging

# Limpieza de consola
logging.getLogger('cmdstanpy').setLevel(logging.WARNING)
logging.getLogger('prophet').setLevel(logging.WARNING)

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

            query = "SELECT timestamp as ds, downstream, upstream FROM traffic_history WHERE olt_name = ? AND port_id = ?"
            df = pd.read_sql_query(query, conn, params=(olt_name, port_id))

            if len(df) < 10:
                print(f"⚠️ {olt_name} {port_id}: Datos insuficientes ({len(df)}/10).")
                continue

            print(f"🧠 Entrenando {olt_name} - Puerto {port_id}...")

            for mode in ['downstream', 'upstream']:
                # 1. Preparar los datos con el CAP de 10Gbps
                train_df = df[['ds', mode]].rename(columns={mode: 'y'})
                train_df['cap'] = 10000  # Techo lógico para el crecimiento logístico

                # 2. Configurar el modelo UNIFICANDO todos los ajustes
                m = Prophet(
                    growth='logistic',  # Usa el CAP de 10000 como límite
                    daily_seasonality=True,  # Patrón día/noche de TeleRed
                    weekly_seasonality=False,  # Desactivar hasta tener 14+ días de data
                    changepoint_prior_scale=0.01,  # Tendencia más rígida (evita caídas falsas)
                    seasonality_prior_scale=1.0  # Da peso a los ciclos diarios
                )

                # 3. Entrenar (UNA sola vez)
                m.fit(train_df)

                # 4. Guardar modelo
                file_name = f"model_{olt_name}_{port_id.replace('/', '_')}_{mode}.json"
                with open(file_name, 'w') as f:
                    f.write(model_to_json(m))

            print(f"✅ Modelos actualizados para {port_id}")

    conn.close()


if __name__ == "__main__":
    train_all()