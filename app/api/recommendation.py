"""Endpoint de recomendación diaria."""
from fastapi import APIRouter, HTTPException
from typing import Optional

from app.config import settings
from app.core.strategy import StrategyEngine
from app.data.candle_repository import CandleRepository

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
        
        # Generar recomendación
        recommendation = strategy_engine.generate_recommendation(
            symbol=symbol,
            interval=interval,
            candles=candles
        )
        
        # Preparar respuesta
        response = recommendation.to_dict()
        response["as_of"] = metadata.get("as_of")
        response["data_freshness"] = candle_repo.get_freshness(symbol, interval)
        
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

