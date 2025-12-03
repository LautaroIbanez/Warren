"""Worker de ingestion - descarga velas de Binance y las guarda."""
import requests
from typing import Optional
import pandas as pd
from datetime import datetime, timedelta

from app.config import settings
from app.data.candle_repository import CandleRepository


class IngestionWorker:
    """Worker para obtener velas de Binance y guardarlas localmente."""
    
    def __init__(self, candle_repo: Optional[CandleRepository] = None):
        self.candle_repo = candle_repo or CandleRepository()
        self.api_url = settings.BINANCE_API_URL
    
    def fetch_klines(
        self,
        symbol: str,
        interval: str,
        limit: int = 500
    ) -> pd.DataFrame:
        """
        Descarga klines de Binance.
        
        Args:
            symbol: Símbolo del par (ej: BTCUSDT)
            interval: Intervalo (1m, 5m, 1h, 1d, etc.)
            limit: Número máximo de velas (máx 1000)
        
        Returns:
            DataFrame con columnas: timestamp, open, high, low, close, volume
        """
        url = f"{self.api_url}/klines"
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": min(limit, 1000)
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Error fetching from Binance API: {str(e)}")
        
        if not data:
            return pd.DataFrame()
        
        # Convertir a DataFrame
        df = pd.DataFrame(data, columns=[
            'open_time', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
            'taker_buy_quote', 'ignore'
        ])
        
        # Seleccionar y renombrar columnas necesarias
        df = df[['open_time', 'open', 'high', 'low', 'close', 'volume']].copy()
        df.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        
        # Convertir tipos
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Ordenar por timestamp
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        return df
    
    def refresh(
        self,
        symbol: Optional[str] = None,
        interval: Optional[str] = None
    ) -> dict:
        """
        Refresca datos: descarga velas de Binance y las guarda.
        
        Args:
            symbol: Símbolo (default: config)
            interval: Intervalo (default: config)
        
        Returns:
            Dict con resultado de la operación
        """
        symbol = symbol or settings.DEFAULT_SYMBOL
        interval = interval or settings.DEFAULT_INTERVAL
        
        try:
            # Descargar velas
            candles = self.fetch_klines(symbol, interval, limit=500)
            
            if candles.empty:
                return {
                    "success": False,
                    "symbol": symbol,
                    "interval": interval,
                    "error": "No candles received from Binance",
                    "warnings": []
                }
            
            # Verificar gaps básicos
            warnings = []
            if len(candles) < 100:
                warnings.append(f"Only {len(candles)} candles received (expected more)")
            
            # Guardar
            metadata = self.candle_repo.save(symbol, interval, candles)
            
            return {
                "success": True,
                "symbol": symbol,
                "interval": interval,
                "metadata": metadata,
                "warnings": warnings
            }
        
        except Exception as e:
            return {
                "success": False,
                "symbol": symbol,
                "interval": interval,
                "error": str(e),
                "warnings": []
            }

