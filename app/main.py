"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
import pandas as pd
from datetime import datetime

from app.config import settings
from app.api import recommendation, backtest, market, risk, refresh, health

app = FastAPI(
    title="Warren API",
    description="Paper Trading Recommendation API",
    version="1.0.0"
)

# Custom JSON encoder para pandas Timestamps
def custom_json_encoder(obj):
    """Encoder personalizado para pandas Timestamps."""
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    elif isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

# Sobrescribir el encoder por defecto
import json
from fastapi.responses import JSONResponse

@app.middleware("http")
async def add_json_encoder(request, call_next):
    """Middleware para manejar serialización JSON personalizada."""
    response = await call_next(request)
    return response

# CORS para frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vite default ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers
app.include_router(recommendation.router)
app.include_router(backtest.router)
app.include_router(market.router)
app.include_router(risk.router)
app.include_router(refresh.router)
app.include_router(health.router)


@app.get("/")
async def root():
    """Health check básico."""
    return {
        "app": "Warren",
        "status": "ok",
        "symbol": settings.DEFAULT_SYMBOL,
        "interval": settings.DEFAULT_INTERVAL
    }

