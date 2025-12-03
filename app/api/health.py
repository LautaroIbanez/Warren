"""Endpoint de health check."""
from fastapi import APIRouter
from datetime import datetime

from app.config import settings
from app.data.candle_repository import CandleRepository
from app.data.backtest_repository import BacktestRepository

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health_check():
    """
    Health check que verifica disponibilidad diaria.
    
    Returns:
        Dict con status y detalles de disponibilidad
    """
    symbol = settings.DEFAULT_SYMBOL
    interval = settings.DEFAULT_INTERVAL
    
    candle_repo = CandleRepository()
    backtest_repo = BacktestRepository()
    
    # Verificar existencia de datos
    candles_exist = candle_repo.exists(symbol, interval)
    backtest_exists = backtest_repo.exists(symbol, interval)
    
    # Verificar frescura
    freshness = candle_repo.get_freshness(symbol, interval) if candles_exist else None
    is_fresh = freshness and not freshness.get("is_stale", True) if freshness else False
    
    # Estado general
    status = "ok" if candles_exist and backtest_exists and is_fresh else "degraded"
    
    details = {
        "status": status,
        "timestamp": datetime.now().isoformat(),
        "symbol": symbol,
        "interval": interval,
        "checks": {
            "candles_exist": candles_exist,
            "backtest_exists": backtest_exists,
            "data_fresh": is_fresh,
        },
    }
    
    if freshness:
        details["freshness"] = freshness
    
    if not candles_exist:
        details["message"] = f"Missing candle data for {symbol} {interval}. Run /refresh first."
    elif not is_fresh:
        details["message"] = f"Data is stale: {freshness.get('reason', 'Unknown')}"
    elif not backtest_exists:
        details["message"] = f"Missing backtest data. Run /backtest/run first."
    else:
        details["message"] = "All systems operational"
    
    return details

