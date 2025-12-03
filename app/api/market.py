"""Endpoint de datos de mercado."""
from fastapi import APIRouter, HTTPException
from typing import Optional

from app.config import settings
from app.data.candle_repository import CandleRepository

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/candles")
async def get_candles(
    symbol: Optional[str] = None,
    interval: Optional[str] = None
):
    """
    Obtiene velas OHLCV para renderizar en el gráfico.
    
    Returns:
        Dict con candles (lista de dicts), metadata (as_of, rows, source_file_hash)
    """
    symbol = symbol or settings.DEFAULT_SYMBOL
    interval = interval or settings.DEFAULT_INTERVAL
    
    candle_repo = CandleRepository()
    
    try:
        candles, metadata = candle_repo.load(symbol, interval)
        
        # Convertir a lista de dicts para JSON
        candles_list = candles.to_dict('records')
        
        # Convertir timestamps a ISO strings
        for candle in candles_list:
            if 'timestamp' in candle and hasattr(candle['timestamp'], 'isoformat'):
                candle['timestamp'] = candle['timestamp'].isoformat()
        
        # Verificar frescura
        freshness = candle_repo.get_freshness(symbol, interval)
        warnings = []
        if freshness and freshness.get('is_stale'):
            warnings.append(freshness.get('reason', 'Data may be stale'))
        
        # Obtener timestamp de última vela
        latest_candle = candles.iloc[-1] if not candles.empty else None
        latest_candle_timestamp = None
        if latest_candle is not None and 'timestamp' in latest_candle:
            latest_candle_timestamp = latest_candle['timestamp']
            if hasattr(latest_candle_timestamp, 'isoformat'):
                latest_candle_timestamp = latest_candle_timestamp.isoformat()
            else:
                latest_candle_timestamp = str(latest_candle_timestamp)
        
        return {
            "candles": candles_list,
            "metadata": {
                **metadata,
                "freshness": freshness,
                "latest_candle_timestamp": latest_candle_timestamp,
                "candles_hash": metadata.get("source_file_hash")
            },
            "warnings": warnings
        }
    
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

