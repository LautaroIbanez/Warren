"""Endpoint de recomendación diaria."""
from fastapi import APIRouter, HTTPException
from typing import Optional
import pandas as pd

from app.config import settings
from app.core.strategy import StrategyEngine
from app.core.backtest import evaluate_risk_for_signal
from app.data.candle_repository import CandleRepository
from app.data.validation import validate_data_window, validate_gaps, validate_data_quality
from app.data.risk_repository import RiskRepository
from datetime import datetime, timedelta

router = APIRouter(prefix="/recommendation", tags=["recommendation"])


@router.get("/today")
async def get_today_recommendation(
    symbol: Optional[str] = None,
    interval: Optional[str] = None
):
    """
    Obtiene la recomendación del día basada en la estrategia.
    
    Returns:
        Dict con signal, confidence, entry_price, stop_loss, take_profit, rationale
    """
    symbol = symbol or settings.DEFAULT_SYMBOL
    interval = interval or settings.DEFAULT_INTERVAL
    
    candle_repo = CandleRepository()
    strategy_engine = StrategyEngine()
    
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
                    "message": f"Data contains {len(gaps)} gaps exceeding maximum allowed ({gaps_metadata.get('max_gap_days')} days)",
                    "symbol": symbol,
                    "interval": interval,
                    "gaps": gaps,
                    "metadata": gaps_metadata
                }
            )
        
        # Validar frescura de última vela (si es muy antigua, no hay señal nueva)
        latest_candle_timestamp = candles['timestamp'].max()
        latest_candle_timestamp_str = latest_candle_timestamp.isoformat() if pd.notna(latest_candle_timestamp) else None
        
        # Calcular antigüedad de última vela
        if pd.notna(latest_candle_timestamp):
            latest_dt = pd.to_datetime(latest_candle_timestamp)
            now_dt = pd.Timestamp.now(tz=latest_dt.tz) if latest_dt.tz else pd.Timestamp.now()
            hours_old = (now_dt - latest_dt).total_seconds() / 3600
            
            # Para velas diarias, si la última vela es > 36 horas antigua, no hay señal nueva
            if interval == "1d" and hours_old > 36:
                return {
                    "signal": "HOLD",
                    "confidence": 0.0,
                    "entry_price": None,
                    "stop_loss": None,
                    "take_profit": None,
                    "rationale": f"No new signal available. Last candle is {hours_old:.1f} hours old (expected daily updates).",
                    "as_of": metadata.get("as_of"),
                    "signal_timestamp": latest_candle_timestamp_str,
                    "data_freshness": candle_repo.get_freshness(symbol, interval),
                    "data_window": {
                        "from_date": metadata.get("from_date"),
                        "to_date": metadata.get("to_date"),
                        "window_days": metadata.get("window_days"),
                        "is_sufficient": True
                    },
                    "candles_hash": metadata.get("source_file_hash"),
                    "is_stale_signal": True,
                    "stale_reason": f"Last candle is {hours_old:.1f} hours old"
                }
        
        # Evaluar riesgo usando función centralizada
        risk_repo = RiskRepository()
        candles_hash = metadata.get("source_file_hash")
        candles_as_of = metadata.get("as_of")
        
        risk_data, cache_validation = risk_repo.load(symbol, interval, candles_hash, candles_as_of)
        
        # Evaluar si la señal debe ser bloqueada
        risk_evaluation = evaluate_risk_for_signal(
            risk_metrics=risk_data.get("metrics", {}) if risk_data else None,
            risk_validation=risk_data.get("validation", {}) if risk_data else None,
            cache_validation=cache_validation
        )
        
        # Si la señal está bloqueada o los datos están obsoletos, retornar respuesta bloqueada
        if risk_evaluation["is_blocked"] or risk_evaluation["is_stale"]:
            block_reason = risk_evaluation["block_reason"] or risk_evaluation["stale_reason"] or "Signal blocked due to risk evaluation"
            block_reasons = risk_evaluation["block_reasons"] or [block_reason]
            
            # Construir rationale detallado
            rationale_parts = [f"Señal bloqueada: {block_reason}"]
            if len(block_reasons) > 1:
                rationale_parts.append("Razones adicionales:")
                for reason in block_reasons[1:]:
                    rationale_parts.append(f"  - {reason}")
            
            # Incluir métricas si están disponibles
            if risk_data:
                risk_metrics = risk_data.get("metrics", {})
                metrics_info = []
                if "profit_factor" in risk_metrics:
                    metrics_info.append(f"Profit Factor: {risk_metrics['profit_factor']:.2f}")
                if "total_return" in risk_metrics:
                    metrics_info.append(f"Retorno Total: {risk_metrics['total_return']:.2f}%")
                if "max_drawdown" in risk_metrics:
                    metrics_info.append(f"Max Drawdown: {risk_metrics['max_drawdown']:.2f}%")
                if "total_trades" in risk_metrics:
                    metrics_info.append(f"Total Trades: {risk_metrics['total_trades']}")
                
                if metrics_info:
                    rationale_parts.append("Métricas del backtest: " + ", ".join(metrics_info))
            
            return {
                "signal": "HOLD",
                "confidence": 0.0,
                "entry_price": None,
                "stop_loss": None,
                "take_profit": None,
                "rationale": ". ".join(rationale_parts),
                "as_of": metadata.get("as_of"),
                "signal_timestamp": latest_candle_timestamp_str,
                "data_freshness": candle_repo.get_freshness(symbol, interval),
                "data_window": {
                    "from_date": metadata.get("from_date"),
                    "to_date": metadata.get("to_date"),
                    "window_days": metadata.get("window_days"),
                    "is_sufficient": True
                },
                "candles_hash": metadata.get("source_file_hash"),
                "is_blocked": True,
                "block_reason": block_reason,
                "block_reasons": block_reasons,
                "is_stale": risk_evaluation["is_stale"],
                "stale_reason": risk_evaluation["stale_reason"]
            }
        
        # Generar recomendación
        recommendation = strategy_engine.generate_recommendation(
            symbol=symbol,
            interval=interval,
            candles=candles
        )
        
        # Preparar respuesta
        response = recommendation.to_dict()
        response["as_of"] = metadata.get("as_of")  # Timestamp de última vela en archivo
        response["signal_timestamp"] = latest_candle_timestamp_str  # Timestamp de vela usada para señal
        response["data_freshness"] = candle_repo.get_freshness(symbol, interval)
        response["data_window"] = {
            "from_date": metadata.get("from_date"),
            "to_date": metadata.get("to_date"),
            "window_days": metadata.get("window_days"),
            "is_sufficient": True
        }
        response["candles_hash"] = metadata.get("source_file_hash")  # Hash para verificación
        
        return response
    
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

