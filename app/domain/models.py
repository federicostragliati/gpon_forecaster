from dataclasses import dataclass
from datetime import datetime

@dataclass
class TrafficMetric:
    """Representa una captura de tráfico."""
    timestamp: datetime
    downstream: float  # En Mbps (bajada)
    upstream: float # En Mbps (subida)

@dataclass
class ForecastResult:
    """El resultado que devuelve la IA."""
    target_date: datetime
    down_predicted: float
    up_predicted: float
    down_upper: float  # Para saber el máximo posible de saturación
    up_upper: float