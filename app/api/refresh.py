"""Endpoint de refresh - actualiza datos desde Binance."""
from fastapi import APIRouter, HTTPException

from app.config import settings
from app.data.ingestion import IngestionWorker
from app.api.recommendation import get_today_recommendation
from app.api.backtest import get_latest_backtest
from app.api.market import get_candles
from app.api.risk import get_risk_metrics

router = APIRouter(prefix="/refresh", tags=["refresh"])


@router.post("")
async def refresh_data(
    symbol: str = None,
    interval: str = None
):
    """
    Refresca datos: descarga velas de Binance, actualiza recomendación y backtest.
    
    Returns:
        Dict con resultado del refresh y snapshots actualizados
    """
    symbol = symbol or settings.DEFAULT_SYMBOL
    interval = interval or settings.DEFAULT_INTERVAL
    
    worker = IngestionWorker()
    
    # Ejecutar refresh de ingestion
    refresh_result = worker.refresh(symbol, interval)
    
    if not refresh_result.get("success"):
        raise HTTPException(
            status_code=503,
            detail={
                "status": "refresh_failed",
                "message": refresh_result.get("error", "Unknown error"),
                "warnings": refresh_result.get("warnings", [])
            }
        )
    
    # Refrescar snapshots (recomendación, backtest, candles, risk)
    try:
        recommendation = await get_today_recommendation(symbol, interval)
    except Exception as e:
        recommendation = {"error": str(e)}
    
    try:
        backtest = await get_latest_backtest(symbol, interval, force_refresh=True)
    except Exception as e:
        backtest = {"error": str(e)}
    
    try:
        candles = await get_candles(symbol, interval)
    except Exception as e:
        candles = {"error": str(e)}
    
    try:
        risk = await get_risk_metrics(symbol, interval)
    except Exception as e:
        risk = {"error": str(e)}
    
    return {
        "refresh": refresh_result,
        "snapshots": {
            "recommendation": recommendation,
            "backtest": backtest,
            "candles": candles,
            "risk": risk
        }
    }

