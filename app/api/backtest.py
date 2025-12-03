"""Endpoint de backtest."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional
import json
import pandas as pd

from app.config import settings
from app.core.backtest import BacktestEngine
from app.core.strategy import StrategyEngine
from app.data.candle_repository import CandleRepository
from app.data.backtest_repository import BacktestRepository

router = APIRouter(prefix="/backtest", tags=["backtest"])


@router.get("/latest")
async def get_latest_backtest(
    symbol: Optional[str] = None,
    interval: Optional[str] = None,
    force_refresh: bool = False
):
    """
    Obtiene el último backtest (cached o re-ejecuta si force_refresh=True).
    
    Returns:
        Dict con trades, equity_curve, metrics y metadata
    """
    symbol = symbol or settings.DEFAULT_SYMBOL
    interval = interval or settings.DEFAULT_INTERVAL
    
    candle_repo = CandleRepository()
    backtest_repo = BacktestRepository()
    
    # Intentar cargar cached si no se fuerza refresh
    if not force_refresh:
        cached = backtest_repo.load(symbol, interval)
        if cached:
            return {
                "cached": True,
                **cached
            }
    
    try:
        # Cargar velas
        candles, metadata = candle_repo.load(symbol, interval)
        
        # Ejecutar backtest
        strategy_engine = StrategyEngine()
        backtest_engine = BacktestEngine(strategy_engine)
        result = backtest_engine.run(symbol, interval, candles)
        
        # Guardar resultado
        backtest_repo.save(
            symbol=symbol,
            interval=interval,
            result=result,
            candles_hash=metadata.get("source_file_hash"),
            candles_timestamp=metadata.get("as_of")
        )
        
        # Preparar respuesta (asegurar serialización JSON)
        response = result.to_dict()
        response["cached"] = False
        # Convertir metadata timestamps a strings
        candles_as_of = metadata.get("as_of")
        if candles_as_of and hasattr(candles_as_of, 'isoformat'):
            candles_as_of = candles_as_of.isoformat()
        response["metadata"] = {
            "symbol": symbol,
            "interval": interval,
            "candles_hash": str(metadata.get("source_file_hash", "")),
            "candles_as_of": str(candles_as_of) if candles_as_of else None
        }
        
        # Añadir warning si no hay trades
        if len(result.trades) == 0:
            response["warning"] = "No trades generated in backtest"
        
        # Usar JSONResponse con encoder personalizado para timestamps
        def json_serial(obj):
            """JSON serializer para objetos no serializables por defecto."""
            if isinstance(obj, pd.Timestamp):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")
        
        return JSONResponse(content=json.loads(json.dumps(response, default=json_serial)))
    
    except FileNotFoundError:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "data_missing",
                "message": f"No candle data found for {symbol} {interval}. Please run /refresh first.",
                "symbol": symbol,
                "interval": interval
            }
        )
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail={
                "status": "data_error",
                "message": str(e),
                "symbol": symbol,
                "interval": interval
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": f"Unexpected error: {str(e)}"
            }
        )


@router.post("/run")
async def run_backtest(
    symbol: Optional[str] = None,
    interval: Optional[str] = None
):
    """
    Ejecuta un nuevo backtest (alias de GET /backtest/latest?force_refresh=true).
    """
    return await get_latest_backtest(symbol, interval, force_refresh=True)

