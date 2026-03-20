from .infrastructure.forecaster_adapter import ProphetForecaster
from .infrastructure.sqlite_repository import SQLiteTrafficRepository
from .application.services import TrafficForecastService
from fastapi import FastAPI, Query
from fastapi import FastAPI, Query

import json
from fastapi.responses import HTMLResponse
from fastapi.responses import StreamingResponse # Asegúrate de importar esto
from .application.services import TrafficForecastService
from .infrastructure.forecaster_adapter import ProphetForecaster
from .infrastructure.sqlite_repository import SQLiteTrafficRepository
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import FileResponse # Importar esto para enviar archivos
import os

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

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


@app.get("/graph/{olt_name}/{port_id:path}", response_class=HTMLResponse)
def get_interactive_graph(olt_name: str, port_id: str):
    html_content = visualize_forecast.generate_interactive_graph(olt_name, port_id)

    if not html_content:
        raise HTTPException(status_code=404, detail="Modelos no encontrados. Ejecute el entrenamiento primero.")

    return html_content

@app.get("/graph/{olt_name}/{port_id:path}")
def get_olt_port_graph(olt_name: str, port_id: str):
    """
    URL de ejemplo: http://127.0.0.1:8000/graph/OLT-SM03/0/8/0
    """
    # 1. Llamamos al generador de gráficos
    img_path = visualize_forecast.generate_dual_graph(olt_name, port_id)

    if not img_path:
        raise HTTPException(status_code=404, detail=f"No hay suficientes datos para {olt_name} en el puerto {port_id}")

    # 2. Servimos el archivo al navegador
    return FileResponse(img_path, media_type="image/png")

if not os.path.exists("static"): os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_index():
    # Servimos el dashboard al entrar a la IP del servidor
    return FileResponse('static/index.html')

@app.get("/config-data")
async def get_config():
    # Endpoint para que el JavaScript sepa qué OLTs y puertos mostrar
    with open("config.json", "r") as f:
        return json.load(f)