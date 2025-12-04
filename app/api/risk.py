"""Endpoint de métricas de riesgo."""
from fastapi import APIRouter, HTTPException
from typing import Optional
import json

from app.config import settings
from app.data.risk_repository import RiskRepository
from app.data.backtest_repository import BacktestRepository
from app.data.candle_repository import CandleRepository

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
    candle_repo = CandleRepository()
    
    # Obtener metadata de velas actuales para validación de cache
    candles_hash = None
    candles_as_of = None
    from_date = None
    to_date = None
    window_days = 0
    
    try:
        _, candle_metadata = candle_repo.load(symbol, interval)
        candles_hash = candle_metadata.get("source_file_hash")
        candles_as_of = candle_metadata.get("as_of")
        from_date = candle_metadata.get("from_date")
        to_date = candle_metadata.get("to_date")
        window_days = candle_metadata.get("window_days", 0)
    except Exception:
        pass  # Si no hay velas, continuar sin validación de cache
    
    # Intentar cargar desde risk repository (con validación de cache)
    risk_data, cache_validation = risk_repo.load(symbol, interval, candles_hash, candles_as_of)
    
    # Si cache es válido, retornarlo
    if risk_data and not cache_validation.get("is_stale") and not cache_validation.get("is_inconsistent"):
        # Verificar si es confiable
        validation = risk_data.get("validation", {})
        metrics = risk_data.get("metrics", {})
        is_reliable = metrics.get("is_reliable", False) or validation.get("is_reliable", False)
        
        # Obtener backtest_hash si está disponible en backtest
        backtest_hash = None
        try:
            backtest_data, _ = backtest_repo.load(symbol, interval, candles_hash, candles_as_of)
            if backtest_data:
                backtest_metadata = backtest_data.get("metadata", {})
                backtest_hash = backtest_metadata.get("backtest_hash")
        except Exception:
            pass
        
        # Obtener backtest_period del backtest si está disponible
        backtest_period = None
        if backtest_data:
            backtest_metadata = backtest_data.get("metadata", {})
            backtest_data_window = backtest_metadata.get("data_window", {})
            if backtest_data_window:
                backtest_period = {
                    "from_date": backtest_data_window.get("from_date"),
                    "to_date": backtest_data_window.get("to_date"),
                    "window_days": backtest_data_window.get("window_days")
                }
        
        # Si no hay backtest_period, usar data_window de risk_data
        if not backtest_period:
            risk_data_window = risk_data.get("data_window", {})
            if risk_data_window:
                backtest_period = {
                    "from_date": risk_data_window.get("from_date"),
                    "to_date": risk_data_window.get("to_date"),
                    "window_days": risk_data_window.get("window_days")
                }
        
        # Obtener last_updated del cache o del backtest
        last_updated = None
        if risk_data.get("saved_at"):
            last_updated = risk_data.get("saved_at")
        elif backtest_data:
            backtest_metadata = backtest_data.get("metadata", {})
            if backtest_metadata.get("candles_as_of"):
                last_updated = backtest_metadata.get("candles_as_of")
        
        return {
            "metrics": metrics,
            "validation": validation,
            "data_window": risk_data.get("data_window", {}),
            "backtest_period": backtest_period,  # Período del backtest usado
            "candles_hash": candles_hash,
            "backtest_hash": backtest_hash,
            "last_updated": last_updated,  # Última actualización
            "cache_info": {
                "cached": True,
                "computed": False,
                "cache_validation": cache_validation,
                "last_updated": last_updated
            },
            "status": "ok" if is_reliable else "degraded",
            "reason": metrics.get("reason") or validation.get("reason") or ("Insufficient data" if not is_reliable else None)
        }
    
    # Cache inválido o no existe - recomputar desde backtest
    
    # Si no existe en risk repo o está obsoleto, calcular desde backtest
    backtest_data = None
    backtest_validation = None
    try:
        backtest_data, backtest_validation = backtest_repo.load(symbol, interval, candles_hash, candles_as_of)
    except (ValueError, json.JSONDecodeError, TypeError) as e:
        # Archivo corrupto o error de parsing, continuar sin datos
        backtest_data = None
        backtest_validation = {"reason": f"Error loading backtest: {str(e)}"}
    except Exception as e:
        # Otro error, continuar sin datos
        backtest_data = None
        backtest_validation = {"reason": f"Error: {str(e)}"}
    
    if backtest_data and backtest_data.get("metrics"):
        metrics = backtest_data.get("metrics", {})
        trades = backtest_data.get("trades", [])
        trade_count = len(trades)
        
        # Usar window_days de metadata de velas si está disponible
        if not window_days:
            window_days = max(trade_count * 2, 30)  # Estimación fallback
        
        is_reliable = metrics.get("is_reliable", False)
        
        # Información sobre si fue recomputado
        was_recomputed = cache_validation.get("is_stale") or cache_validation.get("is_inconsistent") or not risk_data
        
        # Obtener backtest_hash del backtest usado
        backtest_hash = None
        if backtest_data:
            backtest_metadata = backtest_data.get("metadata", {})
            backtest_hash = backtest_metadata.get("backtest_hash")
        
        # Obtener backtest_period del backtest
        backtest_period = None
        if backtest_data:
            backtest_metadata = backtest_data.get("metadata", {})
            backtest_data_window = backtest_metadata.get("data_window", {})
            if backtest_data_window:
                backtest_period = {
                    "from_date": backtest_data_window.get("from_date"),
                    "to_date": backtest_data_window.get("to_date"),
                    "window_days": backtest_data_window.get("window_days")
                }
        
        # Si no hay backtest_period, usar data_window de candles
        if not backtest_period:
            backtest_period = {
                "from_date": from_date,
                "to_date": to_date,
                "window_days": window_days
            }
        
        # Guardar en risk repo para futuro (con metadata de velas)
        save_result = risk_repo.save(
            symbol=symbol,
            interval=interval,
            metrics=metrics,
            trade_count=trade_count,
            window_days=window_days,
            candles_hash=candles_hash,
            candles_as_of=candles_as_of,
            from_date=from_date,
            to_date=to_date
        )
        
        # Obtener last_updated del save o del backtest
        last_updated = None
        if save_result.get("saved_at"):
            last_updated = save_result.get("saved_at")
        elif backtest_data:
            backtest_metadata = backtest_data.get("metadata", {})
            if backtest_metadata.get("candles_as_of"):
                last_updated = backtest_metadata.get("candles_as_of")
        
        return {
            "metrics": metrics,
            "validation": {
                "trade_count": trade_count,
                "window_days": window_days,
                "min_trades_required": settings.MIN_TRADES_FOR_RELIABILITY,
                "min_window_days": settings.MIN_DATA_WINDOW_DAYS,
                "is_reliable": is_reliable
            },
            "data_window": {
                "from_date": from_date,
                "to_date": to_date,
                "window_days": window_days
            },
            "backtest_period": backtest_period,  # Período del backtest usado
            "candles_hash": candles_hash,
            "backtest_hash": backtest_hash,
            "last_updated": last_updated,  # Última actualización
            "cache_info": {
                "cached": False,
                "computed": True,
                "was_recomputed": was_recomputed,
                "previous_cache_validation": cache_validation if was_recomputed else None,
                "last_updated": last_updated
            },
            "status": "ok" if is_reliable else "degraded",
            "reason": metrics.get("reason") or (None if is_reliable else f"Only {trade_count} trades (need {settings.MIN_TRADES_FOR_RELIABILITY}+)")
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

