import json
import time
import sys
from app.infrastructure.snmp_adapter import HuaweiSnmpAdapter
from app.infrastructure.sqlite_repository import SQLiteTrafficRepository


def start_polling():
    print("🚀 Cargando configuración desde config.json...")
    repo = SQLiteTrafficRepository()

    try:
        with open("config.json", "r") as f:
            config = json.load(f)
    except FileNotFoundError:
        print("❌ ERROR: No se encontró el archivo config.json")
        return

    print(f"📡 Monitoreo activo para {len(config['olts'])} OLTs.")

    while True:
        for olt in config["olts"]:
            print(f"🏢 Consultando OLT: {olt['name']} ({olt['ip']})")
            adapter = HuaweiSnmpAdapter(olt["ip"], olt["community"])

            for port in olt["ports"]:
                up, down = adapter.get_current_traffic(port["index"])

                # --- FILTRO GATEKEEPER ---
                # Solo guardamos si:
                # 1. No son None (no hubo error de timeout)
                # 2. Al menos uno de los dos es mayor a cero (hay tráfico real)
                if up is not None and down is not None and (up > 0 or down > 0):
                    repo.save_metric(olt["name"], port["id"], down, up)
                    print(f"  ✅ {port['id']}: {down} Mbps Down / {up} Mbps Up")
                else:
                    # Esto saldrá en tu consola pero no irá a la base de datos
                    razon = "Timeout" if up is None else "Tráfico en cero"
                    print(f"  ⚠️ {port['id']}: Lectura ignorada ({razon})")

        # El sleep va AQUÍ, al final de recorrer todas las OLTs
        interval = config.get("polling_interval", 60)
        print(f"😴 Ciclo completado. Esperando {interval}s para la próxima lectura...")
        time.sleep(interval)


# ESTO TIENE QUE ESTAR EN LA COLUMNA 0 (Sin espacios al principio)
if __name__ == "__main__":
    # Forzamos que los prints se vean en la consola de PyCharm al instante
    sys.stdout.reconfigure(line_buffering=True)
    start_polling()