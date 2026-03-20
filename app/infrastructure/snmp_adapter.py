import time
import asyncio
from pysnmp.hlapi.v3arch.asyncio import (
    getCmd, SnmpEngine, CommunityData,
    UdpTransportTarget, ContextData, ObjectType, ObjectIdentity
)


class HuaweiSnmpAdapter:
    def __init__(self, ip: str, community: str):
        self.ip = ip
        self.community = community
        self.OID_UP = '1.3.6.1.2.1.31.1.1.1.6.'
        self.OID_DOWN = '1.3.6.1.2.1.31.1.1.1.10.'

    def _get_single_value(self, oid: str):
        async def run_query():
            # --- MEJORA 1: Aumentamos el Timeout a 10 segundos y agregamos 3 reintentos ---
            transport = await UdpTransportTarget.create(
                (self.ip, 161),
                timeout=10,
                retries=3
            )

            iterator = await getCmd(
                SnmpEngine(),
                CommunityData(self.community),
                transport,
                ContextData(),
                ObjectType(ObjectIdentity(oid))
            )
            errorIndication, errorStatus, errorIndex, varBinds = iterator

            if errorIndication:
                # Si hay error de red, imprimimos pero devolvemos None
                print(f"❌ Error SNMP en {self.ip}: {errorIndication}")
                return None

            val = varBinds[0][1]
            if not val or str(val) == "" or str(val) == 'None':
                return None

            return int(val)

        try:
            return asyncio.run(run_query())
        except Exception as e:
            print(f"❌ Excepción en query: {e}")
            return None

    def get_current_traffic(self, port_index: str, interval: int = 20):
        # Muestra 1
        in_1 = self._get_single_value(self.OID_UP + str(port_index))
        out_1 = self._get_single_value(self.OID_DOWN + str(port_index))
        t1 = time.time()

        # --- MEJORA 2: Cambiamos 0.0 por None para que el worker sepa que falló ---
        if in_1 is None or out_1 is None:
            return None, None

        print(f"⏳ Delta OK para {port_index}, esperando {interval}s...")
        time.sleep(interval)

        # Muestra 2
        in_2 = self._get_single_value(self.OID_UP + str(port_index))
        out_2 = self._get_single_value(self.OID_DOWN + str(port_index))
        t2 = time.time()

        if in_2 is None or out_2 is None:
            return None, None

        # app/infrastructure/snmp_adapter.py (Línea ~75)
        delta_t = t2 - t1

        # --- SOLUCIÓN: Validar que el contador no haya vuelto a cero ---
        if in_2 < in_1 or out_2 < out_1:
            return None, None  # Ignoramos la muestra si hubo un wrap

        mbps_up = ((in_2 - in_1) * 8) / (delta_t * 1_000_000)
        mbps_down = ((out_2 - out_1) * 8) / (delta_t * 1_000_000)

        # Filtro de cordura para UpLink 10G
        if mbps_up > 10500 or mbps_down > 10500:
            return None, None

        return round(mbps_up, 2), round(mbps_down, 2)  # Quitamos el abs()