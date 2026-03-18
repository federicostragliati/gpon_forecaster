from fastapi import FastAPI, Query
from .infrastructure.forecaster_adapter import ProphetForecaster
from .infrastructure.sqlite_repository import SQLiteTrafficRepository
from .application.services import TrafficForecastService

app = FastAPI(title="Huawei OLT Traffic Forecaster")

# Inyección de dependencias
repo = SQLiteTrafficRepository()
engine = ProphetForecaster()
service = TrafficForecastService(engine, repo)


@app.get("/predict")
def get_prediction(
        port: str = Query(..., description="Nombre del puerto, ej: 0/8/0"),
        days: int = Query(1, ge=1, le=7)
):
    results = service.get_forecast_for_port(port, days)

    if not results:
        return {"error": "No hay suficientes datos históricos para este puerto."}

    return {
        "port": port,
        "forecast_days": days,
        "predictions": results
    }