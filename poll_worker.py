import json
import time
from app.infrastructure.snmp_adapter import HuaweiSnmpAdapter
from app.infrastructure.sqlite_repository import SQLiteTrafficRepository


def start_polling():
    repo = SQLiteTrafficRepository()

    # Cargamos la configuración externa
    with open("config.json", "r") as f:
        config = json.load(f)

    print(f"🚀 Iniciando monitoreo escalable...")

    while True:
        for olt in config["olts"]:
            # ... lógica de consulta ...
            for port in olt["ports"]:
                # ... consulta puerto ...
                if up is not None:
                    repo.save_metric(olt["name"], port["id"], down, up)

        # MOVER ESTO AQUÍ (afuera de los bucles)
        print(f"😴 Ciclo completado. Durmiendo {config['polling_interval']}s...")
        time.sleep(config["polling_interval"])