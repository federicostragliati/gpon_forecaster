from ..domain.ports import ForecastEngine
from ..infrastructure.sqlite_repository import SQLiteTrafficRepository
from ..domain.models import ForecastResult


class TrafficForecastService:
    def __init__(self, engine: ForecastEngine, repo: SQLiteTrafficRepository):
        self._engine = engine
        self._repo = repo

    def get_forecast_for_port(self, port_id: str, days: int):
        # 1. Traemos los datos reales de la base de datos
        history_df = self._repo.get_history_for_prophet(port_id)

        # 2. Le pedimos a la IA que prediga
        raw_forecast = self._engine.predict(history_df, horizon_days=days)

        if raw_forecast.empty:
            return []

        # 3. Mapeamos a objetos de dominio (limpios)
        results = []
        for _, row in raw_forecast.tail(20).iterrows():
            results.append(ForecastResult(
                target_date=row['ds'],
                down_predicted=round(row['down_yhat'], 2),
                up_predicted=round(row['up_yhat'], 2),
                down_upper=round(row['down_upper'], 2),
                up_upper=round(row['up_upper'], 2)
            ))
        return results