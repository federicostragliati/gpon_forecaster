import time
import logging
from app.infrastructure.snmp_adapter import HuaweiSnmpAdapter
from app.infrastructure.sqlite_repository import SQLiteTrafficRepository

# Configuración
OLT_IP = "10.0.255.94"
COMMUNITY = "P1n3@ppl33xpr355"
PORTS_TO_MONITOR = {
    "0/8/0": "234946560"
}
INTERVALO_SEGUNDOS = 60  # Para probar ponelo en 60s, en producción usá 900 (15min)

snmp = HuaweiSnmpAdapter(OLT_IP, COMMUNITY)
repo = SQLiteTrafficRepository()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')


def start_polling():
    logging.info(f"🚀 Iniciando monitoreo en OLT {OLT_IP}...")

    while True:
        for port_name, snmp_index in PORTS_TO_MONITOR.items():
            try:
                logging.info(f"📡 Consultando puerto {port_name}...")
                up, down = snmp.get_current_traffic(snmp_index, interval=5)

                if up > 0 or down > 0:
                    repo.save_metric(port_name, down, up)
                    logging.info(f"✅ Guardado {port_name}: Down {down} Mbps | Up {up} Mbps")
                else:
                    logging.warning(f"⚠️ El puerto {port_name} devolvió 0.0 Mbps (¿Está offline?)")

            except Exception as e:
                logging.error(f"❌ Error monitoreando {port_name}: {e}")

        logging.info(f"😴 Durmiendo por {INTERVALO_SEGUNDOS} segundos...")
        time.sleep(INTERVALO_SEGUNDOS)


if __name__ == "__main__":
    start_polling()