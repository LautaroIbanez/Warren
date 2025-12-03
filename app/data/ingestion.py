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
        interval: Optional[str] = None,
        merge_existing: bool = True
    ) -> dict:
        """
        Refresca datos: descarga velas de Binance y las guarda con merge incremental.
        
        Args:
            symbol: Símbolo (default: config)
            interval: Intervalo (default: config)
            merge_existing: Si True, combina con velas existentes
        
        Returns:
            Dict con resultado de la operación incluyendo validación
        """
        from app.data.validation import validate_data_quality
        
        symbol = symbol or settings.DEFAULT_SYMBOL
        interval = interval or settings.DEFAULT_INTERVAL
        
        try:
            # Descargar velas (máximo 1000 de Binance)
            candles = self.fetch_klines(symbol, interval, limit=1000)
            
            if candles.empty:
                return {
                    "success": False,
                    "symbol": symbol,
                    "interval": interval,
                    "error": "No candles received from Binance",
                    "warnings": [],
                    "validation": {"status": "ERROR", "errors": ["No data received"]}
                }
            
            # Guardar con merge incremental
            metadata = self.candle_repo.save(symbol, interval, candles, merge_existing=merge_existing)
            
            # Cargar velas completas (después del merge) para validación
            merged_candles, _ = self.candle_repo.load(symbol, interval)
            
            # Validar calidad de datos
            validation = validate_data_quality(merged_candles, interval)
            
            # Actualizar metadata con validación
            metadata.update({
                "validation_status": validation["status"],
                "is_valid": validation["is_valid"]
            })
            
            warnings = []
            if validation["warnings"]:
                warnings.extend(validation["warnings"])
            if len(candles) < 100:
                warnings.append(f"Only {len(candles)} new candles received (expected more)")
            
            return {
                "success": True,
                "symbol": symbol,
                "interval": interval,
                "metadata": metadata,
                "warnings": warnings,
                "validation": validation
            }
        
        except Exception as e:
            return {
                "success": False,
                "symbol": symbol,
                "interval": interval,
                "error": str(e),
                "warnings": [],
                "validation": {"status": "ERROR", "errors": [str(e)]}
            }

