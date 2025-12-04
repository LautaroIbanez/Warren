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
    # Capturar errores pero continuar con otros snapshots
    snapshots = {}
    errors = {}
    
    def extract_error_message(e: Exception) -> str:
        """Extrae mensaje de error de HTTPException o Exception genérica."""
        if isinstance(e, HTTPException):
            detail = e.detail
            if isinstance(detail, dict):
                return detail.get("message", detail.get("status", str(e)))
            return str(detail) if detail else str(e)
        return str(e)
    
    try:
        snapshots["recommendation"] = await get_today_recommendation(symbol, interval)
    except Exception as e:
        errors["recommendation"] = extract_error_message(e)
        snapshots["recommendation"] = None
    
    try:
        snapshots["backtest"] = await get_latest_backtest(symbol, interval, force_refresh=True)
    except Exception as e:
        errors["backtest"] = extract_error_message(e)
        snapshots["backtest"] = None
    
    try:
        snapshots["candles"] = await get_candles(symbol, interval)
    except Exception as e:
        errors["candles"] = extract_error_message(e)
        snapshots["candles"] = None
    
    try:
        snapshots["risk"] = await get_risk_metrics(symbol, interval)
    except Exception as e:
        errors["risk"] = extract_error_message(e)
        snapshots["risk"] = None
    
    # Si hay errores críticos (todos fallaron), lanzar excepción
    if len(errors) == len(snapshots):
        raise HTTPException(
            status_code=503,
            detail={
                "status": "snapshots_failed",
                "message": "All snapshots failed to refresh",
                "errors": errors,
                "refresh": refresh_result
            }
        )
    
    return {
        "refresh": refresh_result,
        "snapshots": snapshots,
        "errors": errors if errors else None
    }

