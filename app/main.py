from .infrastructure.forecaster_adapter import ProphetForecaster
from .infrastructure.sqlite_repository import SQLiteTrafficRepository
from .application.services import TrafficForecastService
from fastapi import FastAPI, Query
from fastapi import FastAPI, Query

from .application.services import TrafficForecastService
from .infrastructure.forecaster_adapter import ProphetForecaster
from .infrastructure.sqlite_repository import SQLiteTrafficRepository
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import FileResponse # Importar esto para enviar archivos
import os

import visualize_forecast
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

# Agregar a app/main.py
from fastapi.responses import FileResponse
import subprocess


@app.get("/graph/{port_id:path}")
def get_traffic_graph(port_id: str):
    """
    Endpoint para ver el gráfico en el navegador.
    El ':path' permite que acepte las barras '/' del nombre del puerto.
    """
    # 1. Generamos el archivo .png
    img_path = visualize_forecast.generate_port_graph(port_id)

    if not img_path or not os.path.exists(img_path):
        raise HTTPException(status_code=404, detail="No hay datos suficientes para graficar este puerto.")

    # 2. Devolvemos el archivo para que el navegador lo muestre
    return FileResponse(img_path, media_type="image/png")