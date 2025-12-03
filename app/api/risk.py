"""Endpoint de métricas de riesgo."""
from fastapi import APIRouter, HTTPException
from typing import Optional
import json

from app.config import settings
from app.data.risk_repository import RiskRepository
from app.data.backtest_repository import BacktestRepository

router = APIRouter(prefix="/risk", tags=["risk"])


@router.get("/metrics")
async def get_risk_metrics(
    symbol: Optional[str] = None,
    interval: Optional[str] = None
):
    """
    Obtiene métricas de riesgo desde backtests.
    
    Returns:
        Dict con metrics, validation (trade_count, window_days, is_reliable), status
    """
    symbol = symbol or settings.DEFAULT_SYMBOL
    interval = interval or settings.DEFAULT_INTERVAL
    
    risk_repo = RiskRepository()
    backtest_repo = BacktestRepository()
    
    # Intentar cargar desde risk repository
    risk_data = risk_repo.load(symbol, interval)
    if risk_data:
        # Verificar si es confiable
        validation = risk_data.get("validation", {})
        is_reliable = validation.get("is_reliable", False)
        
        return {
            "metrics": risk_data.get("metrics", {}),
            "validation": validation,
            "status": "ok" if is_reliable else "degraded",
            "reason": None if is_reliable else validation.get("reason", "Insufficient data")
        }
    
    # Si no existe en risk repo, intentar calcular desde backtest
    backtest_data = None
    try:
        backtest_data = backtest_repo.load(symbol, interval)
    except (ValueError, json.JSONDecodeError, TypeError) as e:
        # Archivo corrupto o error de parsing, continuar sin datos
        backtest_data = None
    except Exception as e:
        # Otro error, continuar sin datos
        backtest_data = None
    
    if backtest_data and backtest_data.get("metrics"):
        metrics = backtest_data.get("metrics", {})
        trades = backtest_data.get("trades", [])
        trade_count = len(trades)
        
        # Calcular window_days aproximado (necesitaríamos timestamps reales)
        # Por ahora usamos trade_count como proxy
        window_days = max(trade_count * 2, 30)  # Estimación
        
        is_reliable = trade_count >= settings.MIN_TRADES_FOR_RELIABILITY
        
        # Guardar en risk repo para futuro
        risk_repo.save(
            symbol=symbol,
            interval=interval,
            metrics=metrics,
            trade_count=trade_count,
            window_days=window_days
        )
        
        return {
            "metrics": metrics,
            "validation": {
                "trade_count": trade_count,
                "window_days": window_days,
                "min_trades_required": settings.MIN_TRADES_FOR_RELIABILITY,
                "min_window_days": settings.MIN_WINDOW_DAYS,
                "is_reliable": is_reliable
            },
            "status": "ok" if is_reliable else "degraded",
            "reason": None if is_reliable else f"Only {trade_count} trades (need {settings.MIN_TRADES_FOR_RELIABILITY}+)"
        }
    
    # No hay datos
    raise HTTPException(
        status_code=503,
        detail={
            "status": "data_missing",
            "message": f"No risk data found for {symbol} {interval}. Please run /backtest/run first.",
            "symbol": symbol,
            "interval": interval
        }
    )

