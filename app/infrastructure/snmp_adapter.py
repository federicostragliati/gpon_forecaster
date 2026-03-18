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
        # OIDs de 64 bits (ifHCInOctets e ifHCOutOctets) - Más estables en Huawei
        self.OID_UP = '1.3.6.1.2.1.31.1.1.1.6.'  # Upstream (HC)
        self.OID_DOWN = '1.3.6.1.2.1.31.1.1.1.10.'  # Downstream (HC)

    def _get_single_value(self, oid: str):
        async def run_query():
            transport = await UdpTransportTarget.create((self.ip, 161))
            iterator = await getCmd(
                SnmpEngine(),
                CommunityData(self.community),
                transport,
                ContextData(),
                ObjectType(ObjectIdentity(oid))
            )
            errorIndication, errorStatus, errorIndex, varBinds = iterator

            if errorIndication:
                print(f"❌ Error de red: {errorIndication}")
                return None

            val = varBinds[0][1]
            # Verificamos si el valor es nulo o vacío antes de convertir a int
            if not val or str(val) == "":
                print(f"⚠️ OID no encontrado o vacío: {oid}")
                return None

            return int(val)

        try:
            return asyncio.run(run_query())
        except Exception as e:
            print(f"❌ Error inesperado en {oid}: {e}")
            return None

    def get_current_traffic(self, port_index: str, interval: int = 5):
        # Muestra 1
        print(f"🔍 Consultando muestras iniciales para index {port_index}...")
        in_1 = self._get_single_value(self.OID_UP + str(port_index))
        out_1 = self._get_single_value(self.OID_DOWN + str(port_index))
        t1 = time.time()

        if in_1 is None or out_1 is None:
            return 0.0, 0.0

        print(f"⏳ Esperando {interval}s para calcular Delta...")
        time.sleep(interval)

        # Muestra 2
        in_2 = self._get_single_value(self.OID_UP + str(port_index))
        out_2 = self._get_single_value(self.OID_DOWN + str(port_index))
        t2 = time.time()

        if in_2 is None or out_2 is None:
            return 0.0, 0.0

        delta_t = t2 - t1
        mbps_up = ((in_2 - in_1) * 8) / (delta_t * 1_000_000)
        mbps_down = ((out_2 - out_1) * 8) / (delta_t * 1_000_000)

        return round(abs(mbps_up), 2), round(abs(mbps_down), 2)