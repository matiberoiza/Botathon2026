"""
API del MVP «Cada hora cuenta».

Para levantarla (desde la carpeta del proyecto). Con --host 0.0.0.0 acepta conexiones de otros
equipos de la red, como la VM de Blue Prism:
    python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
Documentación interactiva: http://localhost:8000/docs

Al arrancar crea la base SQLite si no existe y hace la carga inicial de parámetros y entradas.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import carga_inicial, config
from .routers import buk, dashboard, salud


@asynccontextmanager
async def al_arrancar(_app: FastAPI):
    try:
        carga_inicial.cargar()
    except FileNotFoundError as error:
        print(f"Aviso: {error}")  # la API arranca igual; /api/salud muestra el estado
    yield


app = FastAPI(
    title="Planificación asistencial Teletón",
    description="Recibe la dotación de BUK desde Blue Prism, calcula horas y metas por profesional y mes, "
                "y entrega los resultados al dashboard.",
    version="0.2.0",
    lifespan=al_arrancar,
)

app.add_middleware(CORSMiddleware, allow_origins=config.ORIGENES_FRONTEND, allow_methods=["*"], allow_headers=["*"])

app.include_router(salud.router)
app.include_router(buk.router)
app.include_router(dashboard.router)
