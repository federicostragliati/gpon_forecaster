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
            adapter = HuaweiSnmpAdapter(olt["ip"], olt["community"])
            print(f"🏢 Consultando OLT: {olt['name']}")

            for port in olt["ports"]:
                up, down = adapter.get_current_traffic(port["index"])
                if up is not None:
                    repo.save_metric(olt["name"], port["id"], down, up)
                    print(f"  ✅ {port['id']}: {down} Mbps / {up} Mbps")

        time.sleep(config["polling_interval"])