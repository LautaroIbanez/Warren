"""Repositorio de velas basado en archivos Parquet."""
import os
from pathlib import Path
from typing import Optional
from datetime import datetime
import pandas as pd
import pyarrow.parquet as pq

from app.config import settings


class CandleRepository:
    """Repositorio para almacenar y cargar velas en formato Parquet."""
    
    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = Path(data_dir or settings.CANDLES_DIR)
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_file_path(self, symbol: str, interval: str) -> Path:
        """Obtiene la ruta del archivo para un símbolo/intervalo."""
        filename = f"{symbol}_{interval}.parquet"
        return self.data_dir / filename
    
    def save(
        self,
        symbol: str,
        interval: str,
        candles: pd.DataFrame
    ) -> dict:
        """
        Guarda velas en archivo Parquet.
        
        Args:
            symbol: Símbolo del par (ej: BTCUSDT)
            interval: Intervalo (ej: 1d)
            candles: DataFrame con columnas: timestamp, open, high, low, close, volume
        
        Returns:
            Dict con metadata del archivo guardado
        """
        if candles.empty:
            raise ValueError("Cannot save empty candles DataFrame")
        
        # Validar columnas requeridas
        required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        missing_cols = [col for col in required_cols if col not in candles.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {', '.join(missing_cols)}")
        
        # Ordenar por timestamp
        candles = candles.sort_values('timestamp').reset_index(drop=True)
        
        # Asegurar tipos correctos
        candles['timestamp'] = pd.to_datetime(candles['timestamp'])
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_cols:
            candles[col] = pd.to_numeric(candles[col], errors='coerce')
        
        # Guardar Parquet
        file_path = self._get_file_path(symbol, interval)
        candles.to_parquet(file_path, index=False, engine='pyarrow')
        
        # Obtener metadata
        latest_timestamp = candles['timestamp'].max()
        row_count = len(candles)
        
        # Calcular hash simple del contenido (usando timestamp de última vela)
        file_hash = str(hash(str(latest_timestamp) + str(row_count)))
        
        return {
            "file_path": str(file_path),
            "as_of": latest_timestamp.isoformat() if pd.notna(latest_timestamp) else None,
            "rows": row_count,
            "source_file_hash": file_hash
        }
    
    def load(
        self,
        symbol: str,
        interval: str
    ) -> tuple[pd.DataFrame, dict]:
        """
        Carga velas desde archivo Parquet.
        
        Args:
            symbol: Símbolo del par
            interval: Intervalo
        
        Returns:
            Tuple (DataFrame, metadata_dict)
        
        Raises:
            FileNotFoundError: Si el archivo no existe
            ValueError: Si el archivo está corrupto o vacío
        """
        file_path = self._get_file_path(symbol, interval)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Candle file not found: {file_path}")
        
        try:
            candles = pd.read_parquet(file_path, engine='pyarrow')
        except Exception as e:
            raise ValueError(f"Error reading parquet file: {str(e)}")
        
        if candles.empty:
            raise ValueError(f"Candle file is empty: {file_path}")
        
        # Validar columnas
        required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        missing_cols = [col for col in required_cols if col not in candles.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns in file: {', '.join(missing_cols)}")
        
        # Asegurar timestamp como datetime
        candles['timestamp'] = pd.to_datetime(candles['timestamp'])
        
        # Ordenar por timestamp
        candles = candles.sort_values('timestamp').reset_index(drop=True)
        
        # Metadata
        latest_timestamp = candles['timestamp'].max()
        row_count = len(candles)
        file_hash = str(hash(str(latest_timestamp) + str(row_count)))
        
        metadata = {
            "file_path": str(file_path),
            "as_of": latest_timestamp.isoformat() if pd.notna(latest_timestamp) else None,
            "rows": row_count,
            "source_file_hash": file_hash,
            "exists": True
        }
        
        return candles, metadata
    
    def exists(self, symbol: str, interval: str) -> bool:
        """Verifica si existe archivo para símbolo/intervalo."""
        file_path = self._get_file_path(symbol, interval)
        return file_path.exists()
    
    def get_freshness(
        self,
        symbol: str,
        interval: str
    ) -> Optional[dict]:
        """
        Obtiene información de frescura del archivo.
        
        Returns:
            Dict con 'as_of', 'is_stale', 'hours_old' o None si no existe
        """
        if not self.exists(symbol, interval):
            return None
        
        try:
            _, metadata = self.load(symbol, interval)
            as_of_str = metadata.get('as_of')
            
            if not as_of_str:
                return {
                    "as_of": None,
                    "is_stale": True,
                    "hours_old": None,
                    "reason": "No timestamp in file"
                }
            
            as_of = pd.to_datetime(as_of_str)
            now = pd.Timestamp.now(tz=as_of.tz) if as_of.tz else pd.Timestamp.now()
            hours_old = (now - as_of).total_seconds() / 3600
            
            is_stale = hours_old > settings.STALE_CANDLE_HOURS
            
            return {
                "as_of": as_of_str,
                "is_stale": is_stale,
                "hours_old": round(hours_old, 2),
                "reason": f"Data is {hours_old:.1f} hours old" if is_stale else "Data is fresh"
            }
        except Exception as e:
            return {
                "as_of": None,
                "is_stale": True,
                "hours_old": None,
                "reason": f"Error checking freshness: {str(e)}"
            }

