import json
import time
import sys
import logging
from app.infrastructure.snmp_adapter import HuaweiSnmpAdapter
from app.infrastructure.sqlite_repository import SQLiteTrafficRepository

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

REQUIRED_OLT_KEYS = {"name", "ip", "community", "ports"}


def validate_config(config):
    """Valida el schema de config.json antes de arrancar el loop."""
    for olt in config.get("olts", []):
        missing = REQUIRED_OLT_KEYS - olt.keys()
        if missing:
            raise ValueError(f"OLT mal configurada, faltan campos: {missing} en {olt}")
    if not config.get("olts"):
        raise ValueError("config.json no tiene OLTs definidas.")


def start_polling():
    log.info("Cargando configuración desde config.json...")
    repo = SQLiteTrafficRepository()

    try:
        with open("config.json", "r") as f_config:
            config = json.load(f_config)
    except FileNotFoundError:
        log.error("No se encontró el archivo config.json")
        return

    try:
        validate_config(config)
    except ValueError as e:
        log.error("Error en config.json: %s", e)
        return

    interval = config.get("polling_interval", 60)
    log.info("Monitoreo activo para %d OLTs. Intervalo: %ds.", len(config["olts"]), interval)

    while True:
        for olt in config["olts"]:
            log.info("Consultando OLT: %s (%s)", olt["name"], olt["ip"])

            # FIX: adaptador instanciado UNA vez por OLT, no por puerto
            adapter = HuaweiSnmpAdapter(olt["ip"], olt["community"])

            for port in olt["ports"]:

                # FIX: try/except para que un error en un puerto no tire el loop entero
                try:
                    up, down = adapter.get_current_traffic(port["index"])
                except Exception as e:
                    log.warning("Error consultando %s en %s: %s", port["id"], olt["name"], e)
                    continue

                # --- FILTRO GATEKEEPER ---
                # Solo guardamos si:
                # 1. No son None (no hubo error de timeout)
                # 2. Al menos uno de los dos es mayor a cero (hay tráfico real)
                if up is not None and down is not None and (up > 0 or down > 0):
                    repo.save_metric(olt["name"], port["id"], down, up)
                    log.info("  %s: %.1f Mbps Down / %.1f Mbps Up", port["id"], down, up)
                else:
                    razon = "Timeout" if up is None else "Tráfico en cero"
                    log.warning("  %s: Lectura ignorada (%s)", port["id"], razon)

        log.info("Ciclo completado. Esperando %ds para la próxima lectura...", interval)
        time.sleep(interval)


if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True)
    start_polling()
