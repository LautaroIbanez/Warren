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
    backtest_repo = BacktestRepository()
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
        
        # Obtener window_days de metadata de velas para validación
        window_days = metadata.get("window_days")
        
        # Evaluar si la señal debe ser bloqueada
        risk_evaluation = evaluate_risk_for_signal(
            risk_metrics=risk_data.get("metrics", {}) if risk_data else None,
            risk_validation=risk_data.get("validation", {}) if risk_data else None,
            cache_validation=cache_validation,
            window_days=window_days
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
            
            # Incluir violaciones estructuradas si están disponibles
            violations = risk_evaluation.get("violations", [])
            if violations:
                rationale_parts.append("Violaciones detectadas:")
                for violation in violations:
                    rationale_parts.append(f"  - {violation.get('message', 'Unknown violation')}")
            
            # Incluir métricas si están disponibles
            if risk_data:
                risk_metrics = risk_data.get("metrics", {})
                metrics_info = []
                pf = risk_metrics.get("profit_factor")
                if pf is not None:
                    metrics_info.append(f"Profit Factor: {pf:.2f}")
                else:
                    # None represents infinity (no losses, only profits)
                    metrics_info.append("Profit Factor: ∞")
                if "total_return" in risk_metrics:
                    metrics_info.append(f"Retorno Total: {risk_metrics['total_return']:.2f}%")
                if "max_drawdown" in risk_metrics:
                    metrics_info.append(f"Max Drawdown: {risk_metrics['max_drawdown']:.2f}%")
                if "total_trades" in risk_metrics:
                    metrics_info.append(f"Total Trades: {risk_metrics['total_trades']}")
                
                if metrics_info:
                    rationale_parts.append("Métricas del backtest: " + ", ".join(metrics_info))
            
            # Obtener información de backtest para incluir período y last_updated
            backtest_period = None
            backtest_hash = None
            last_updated = None
            try:
                backtest_data, _ = backtest_repo.load(symbol, interval, metadata.get("source_file_hash"), metadata.get("as_of"))
                if backtest_data:
                    backtest_metadata = backtest_data.get("metadata", {})
                    backtest_hash = backtest_metadata.get("backtest_hash")
                    backtest_data_window = backtest_metadata.get("data_window", {})
                    if backtest_data_window:
                        backtest_period = {
                            "from_date": backtest_data_window.get("from_date"),
                            "to_date": backtest_data_window.get("to_date"),
                            "window_days": backtest_data_window.get("window_days")
                        }
                    if backtest_metadata.get("candles_as_of"):
                        last_updated = backtest_metadata.get("candles_as_of")
            except Exception:
                pass
            
            # Si no hay backtest_period, usar data_window de candles
            if not backtest_period:
                backtest_period = {
                    "from_date": metadata.get("from_date"),
                    "to_date": metadata.get("to_date"),
                    "window_days": metadata.get("window_days")
                }
            
            return {
                "signal": "HOLD",
                "confidence": 0.0,
                "entry_price": None,
                "stop_loss": None,
                "take_profit": None,
                "rationale": ". ".join(rationale_parts),
                "as_of": metadata.get("as_of"),
                "signal_timestamp": latest_candle_timestamp_str,
                "last_updated": last_updated or metadata.get("as_of"),
                "data_freshness": candle_repo.get_freshness(symbol, interval),
                "data_window": {
                    "from_date": metadata.get("from_date"),
                    "to_date": metadata.get("to_date"),
                    "window_days": metadata.get("window_days"),
                    "is_sufficient": True
                },
                "backtest_period": backtest_period,
                "candles_hash": metadata.get("source_file_hash"),
                "backtest_hash": backtest_hash,
                "is_blocked": True,
                "block_reason": block_reason,
                "block_reasons": block_reasons,
                "violations": risk_evaluation.get("violations", []),
                "is_stale": risk_evaluation["is_stale"],
                "stale_reason": risk_evaluation["stale_reason"]
            }
        
        # Generar recomendación
        recommendation = strategy_engine.generate_recommendation(
            symbol=symbol,
            interval=interval,
            candles=candles
        )
        
        # Obtener información de backtest para incluir período
        backtest_period = None
        backtest_hash = None
        last_updated = None
        try:
            backtest_data, _ = backtest_repo.load(symbol, interval, metadata.get("source_file_hash"), metadata.get("as_of"))
            if backtest_data:
                backtest_metadata = backtest_data.get("metadata", {})
                backtest_hash = backtest_metadata.get("backtest_hash")
                backtest_data_window = backtest_metadata.get("data_window", {})
                if backtest_data_window:
                    backtest_period = {
                        "from_date": backtest_data_window.get("from_date"),
                        "to_date": backtest_data_window.get("to_date"),
                        "window_days": backtest_data_window.get("window_days")
                    }
                # Usar timestamp del backtest como last_updated si está disponible
                if backtest_metadata.get("candles_as_of"):
                    last_updated = backtest_metadata.get("candles_as_of")
        except Exception:
            pass  # Si no hay backtest, continuar sin esa información
        
        # Si no hay backtest_period, usar data_window de candles
        if not backtest_period:
            backtest_period = {
                "from_date": metadata.get("from_date"),
                "to_date": metadata.get("to_date"),
                "window_days": metadata.get("window_days")
            }
        
        # Preparar respuesta
        response = recommendation.to_dict()
        response["as_of"] = metadata.get("as_of")  # Timestamp de última vela en archivo
        response["signal_timestamp"] = latest_candle_timestamp_str  # Timestamp de vela usada para señal
        response["last_updated"] = last_updated or metadata.get("as_of")  # Última actualización (backtest o candles)
        response["data_freshness"] = candle_repo.get_freshness(symbol, interval)
        response["data_window"] = {
            "from_date": metadata.get("from_date"),
            "to_date": metadata.get("to_date"),
            "window_days": metadata.get("window_days"),
            "is_sufficient": True
        }
        response["backtest_period"] = backtest_period  # Período del backtest usado
        response["candles_hash"] = metadata.get("source_file_hash")  # Hash para verificación
        response["backtest_hash"] = backtest_hash  # Hash del backtest usado
        
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

