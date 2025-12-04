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
from app.data.validation import validate_data_window, validate_gaps

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
    
    # Obtener metadata de velas actuales para validación
    candles_hash = None
    candles_as_of = None
    try:
        _, candle_metadata = candle_repo.load(symbol, interval)
        candles_hash = candle_metadata.get("source_file_hash")
        candles_as_of = candle_metadata.get("as_of")
    except Exception:
        pass  # Si no hay velas, continuar sin validación
    
    # Intentar cargar cached si no se fuerza refresh
    if not force_refresh:
        cached, validation_info = backtest_repo.load(symbol, interval, candles_hash, candles_as_of)
        # Solo usar cache si es válido (no stale, no inconsistente)
        if cached and not validation_info.get("is_stale") and not validation_info.get("is_inconsistent"):
            metadata = cached.get("metadata", {})
            return {
                "cached": True,
                "computed": False,
                "cache_validation": validation_info,
                "candles_hash": metadata.get("candles_hash"),
                "backtest_hash": metadata.get("backtest_hash"),
                **cached
            }
        # Si cache está obsoleto, continuar para recomputar
    
    try:
        # Cargar velas
        candles, metadata = candle_repo.load(symbol, interval)
        
        # Validar ventana temporal mínima
        is_valid, error_msg, window_metadata = validate_data_window(candles)
        
        if not is_valid:
            raise HTTPException(
                status_code=503,
                detail={
                    "status": "INSUFFICIENT_DATA",
                    "message": error_msg,
                    "symbol": symbol,
                    "interval": interval,
                    "metadata": window_metadata
                }
            )
        
        # Validar gaps en datos
        is_valid_gaps, gaps, gaps_metadata = validate_gaps(candles, interval)
        if not is_valid_gaps and gaps:
            raise HTTPException(
                status_code=503,
                detail={
                    "status": "DATA_GAPS",
                    "message": f"Data contains {len(gaps)} gaps exceeding maximum allowed ({gaps_metadata.get('max_gap_days')} days). Backtest may be invalid.",
                    "symbol": symbol,
                    "interval": interval,
                    "gaps": gaps,
                    "metadata": gaps_metadata
                }
            )
        
        # Ejecutar backtest (recomputar)
        strategy_engine = StrategyEngine()
        backtest_engine = BacktestEngine(strategy_engine)
        result = backtest_engine.run(symbol, interval, candles)
        
        # Obtener hash y timestamp actualizados
        current_hash = metadata.get("source_file_hash")
        current_as_of = metadata.get("as_of")
        if current_as_of and hasattr(current_as_of, 'isoformat'):
            current_as_of = current_as_of.isoformat()
        elif current_as_of:
            current_as_of = str(current_as_of)
        
        # Guardar resultado con metadata actualizada
        save_result = backtest_repo.save(
            symbol=symbol,
            interval=interval,
            result=result,
            candles_hash=current_hash,
            candles_timestamp=current_as_of
        )
        
        # Preparar respuesta (asegurar serialización JSON)
        response = result.to_dict()
        response["cached"] = False
        response["computed"] = True
        # Convertir metadata timestamps a strings
        candles_as_of_str = metadata.get("as_of")
        if candles_as_of_str and hasattr(candles_as_of_str, 'isoformat'):
            candles_as_of_str = candles_as_of_str.isoformat()
        elif candles_as_of_str:
            candles_as_of_str = str(candles_as_of_str)
        
        backtest_hash = save_result.get("backtest_hash")
        
        response["metadata"] = {
            "symbol": symbol,
            "interval": interval,
            "candles_hash": str(metadata.get("source_file_hash", "")),
            "backtest_hash": backtest_hash,
            "candles_as_of": candles_as_of_str,
            "data_window": {
                "from_date": metadata.get("from_date"),
                "to_date": metadata.get("to_date"),
                "window_days": metadata.get("window_days"),
                "is_sufficient": True
            }
        }
        response["candles_hash"] = str(metadata.get("source_file_hash", ""))
        response["backtest_hash"] = backtest_hash
        response["cache_validation"] = {
            "is_stale": False,
            "is_inconsistent": False,
            "reason": "Freshly computed",
            "cached_hash": None,
            "current_hash": str(metadata.get("source_file_hash", "")),
            "cached_as_of": None,
            "current_as_of": candles_as_of_str
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

