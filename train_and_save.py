import sqlite3
import pandas as pd
from prophet import Prophet
from prophet.serialize import model_to_json
import os
import json
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# Silenciar logs internos de Prophet/Stan
logging.getLogger("cmdstanpy").setLevel(logging.WARNING)
logging.getLogger("prophet").setLevel(logging.WARNING)

DB_PATH = "gpon_monitoring.db"
CONFIG_PATH = "config.json"


def train_all():
    if not os.path.exists(CONFIG_PATH):
        log.error("No existe config.json")
        return

    # FIX: variable renombrada a f_config para evitar colisión con f_model más abajo
    with open(CONFIG_PATH, "r") as f_config:
        config = json.load(f_config)

    # FIX: leer cap y freq desde config para que sean consistentes con el poller
    cap_mbps = config.get("cap_mbps", 10000)
    polling_sec = config.get("polling_interval", 60)
    freq = f"{polling_sec}s"
    # 7 días expresados en cantidad de puntos según el intervalo real de polling
    periods_7d = int(7 * 24 * 3600 / polling_sec)

    log.info("Cap: %d Mbps | Freq: %s | Períodos 7d: %d", cap_mbps, freq, periods_7d)

    # FIX: usar context manager para que la conexión se cierre aunque haya excepciones
    with sqlite3.connect(DB_PATH) as conn:
        for olt in config["olts"]:
            olt_name = olt["name"]
            for port in olt["ports"]:
                port_id = port["id"]

                query = (
                    "SELECT timestamp as ds, downstream, upstream "
                    "FROM traffic_history "
                    "WHERE olt_name = ? AND port_id = ?"
                )
                df = pd.read_sql_query(query, conn, params=(olt_name, port_id))

                if len(df) < 10:
                    log.warning("%s %s: Datos insuficientes (%d/10). Saltando.", olt_name, port_id, len(df))
                    continue

                log.info("Entrenando %s - Puerto %s (%d puntos)...", olt_name, port_id, len(df))

                for mode in ["downstream", "upstream"]:
                    try:
                        # 1. Preparar datos con el CAP configurado
                        train_df = df[["ds", mode]].rename(columns={mode: "y"})
                        train_df["cap"] = cap_mbps

                        # 2. Configurar modelo
                        m = Prophet(
                            growth="logistic",
                            daily_seasonality=True,
                            weekly_seasonality=True,
                            changepoint_prior_scale=0.01,
                            seasonality_prior_scale=1.0,
                        )

                        # 3. Entrenar
                        m.fit(train_df)

                        # 4. Guardar modelo
                        # FIX: variable renombrada a f_model para evitar colisión con f_config
                        file_name = f"model_{olt_name}_{port_id.replace('/', '_')}_{mode}.json"
                        with open(file_name, "w") as f_model:
                            f_model.write(model_to_json(m))

                        log.info("  [%s] Modelo guardado: %s", mode, file_name)

                    except Exception as e:
                        log.error("  Error entrenando %s/%s/%s: %s", olt_name, port_id, mode, e)
                        continue

                log.info("Modelos actualizados para %s", port_id)


if __name__ == "__main__":
    train_all()
