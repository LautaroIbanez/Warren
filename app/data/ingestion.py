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
        limit: int = 1000,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> pd.DataFrame:
        """
        Descarga klines de Binance (una página, máximo 1000).
        
        Args:
            symbol: Símbolo del par (ej: BTCUSDT)
            interval: Intervalo (1m, 5m, 1h, 1d, etc.)
            limit: Número máximo de velas (máx 1000)
            start_time: Timestamp de inicio (opcional)
            end_time: Timestamp de fin (opcional)
        
        Returns:
            DataFrame con columnas: timestamp, open, high, low, close, volume
        """
        url = f"{self.api_url}/klines"
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": min(limit, 1000)
        }
        
        # Añadir timestamps si se proporcionan
        if start_time:
            params["startTime"] = int(start_time.timestamp() * 1000)
        if end_time:
            params["endTime"] = int(end_time.timestamp() * 1000)
        
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
    
    def fetch_klines_paginated(
        self,
        symbol: str,
        interval: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        max_klines: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Descarga klines de Binance con paginación para obtener más de 1000 velas.
        
        Args:
            symbol: Símbolo del par
            interval: Intervalo de tiempo
            start_time: Timestamp de inicio (si None, descarga desde el inicio disponible)
            end_time: Timestamp de fin (si None, descarga hasta ahora)
            max_klines: Máximo número de velas a descargar (None = sin límite)
        
        Returns:
            DataFrame con todas las velas descargadas
        """
        import time
        
        all_candles = []
        current_end = end_time or datetime.now()
        chunk_size = 1000  # Binance máximo por request
        total_downloaded = 0
        
        # Calcular intervalo en días para estimar cuántas velas necesitamos
        interval_days_map = {
            "1m": 1/1440, "5m": 5/1440, "15m": 15/1440, "30m": 30/1440,
            "1h": 1/24, "4h": 4/24, "12h": 12/24,
            "1d": 1, "1w": 7, "1M": 30
        }
        interval_days = interval_days_map.get(interval, 1)
        
        while True:
            # Calcular start_time para este chunk (1000 velas hacia atrás desde current_end)
            chunk_start = current_end - timedelta(days=interval_days * chunk_size)
            if start_time and chunk_start < start_time:
                chunk_start = start_time
            
            # Descargar chunk
            chunk = self.fetch_klines(
                symbol=symbol,
                interval=interval,
                limit=chunk_size,
                start_time=chunk_start,
                end_time=current_end
            )
            
            if chunk.empty:
                break
            
            # Añadir a acumulador
            all_candles.append(chunk)
            total_downloaded += len(chunk)
            
            # Verificar límite
            if max_klines and total_downloaded >= max_klines:
                break
            
            # Si recibimos menos de 1000, hemos llegado al inicio
            if len(chunk) < chunk_size:
                break
            
            # Actualizar current_end para el siguiente chunk (usar el timestamp más antiguo)
            current_end = chunk['timestamp'].min() - timedelta(milliseconds=1)
            
            # Si llegamos al start_time, terminar
            if start_time and current_end <= start_time:
                break
            
            # Rate limiting: esperar un poco para no sobrecargar la API
            time.sleep(0.1)
        
        # Combinar todos los chunks
        if not all_candles:
            return pd.DataFrame()
        
        combined = pd.concat(all_candles, ignore_index=True)
        
        # Eliminar duplicados y ordenar
        combined = combined.drop_duplicates(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)
        
        return combined
    
    def refresh(
        self,
        symbol: Optional[str] = None,
        interval: Optional[str] = None,
        merge_existing: bool = True,
        min_window_days: Optional[int] = None
    ) -> dict:
        """
        Refresca datos: descarga velas de Binance con paginación y las guarda con merge incremental.
        
        Args:
            symbol: Símbolo (default: config)
            interval: Intervalo (default: config)
            merge_existing: Si True, combina con velas existentes
            min_window_days: Días mínimos de histórico a descargar (default: MIN_DATA_WINDOW_DAYS)
        
        Returns:
            Dict con resultado de la operación incluyendo validación
        """
        from app.data.validation import validate_data_quality
        
        symbol = symbol or settings.DEFAULT_SYMBOL
        interval = interval or settings.DEFAULT_INTERVAL
        min_window_days = min_window_days or settings.MIN_DATA_WINDOW_DAYS
        
        try:
            # Calcular fecha de inicio para cumplir con min_window_days
            end_time = datetime.now()
            start_time = end_time - timedelta(days=min_window_days + 30)  # +30 días de margen
            
            # Intentar cargar velas existentes para determinar qué falta
            existing_candles = None
            existing_start = None
            existing_end = None
            
            try:
                existing_candles, existing_metadata = self.candle_repo.load(symbol, interval)
                if not existing_candles.empty:
                    existing_start = existing_candles['timestamp'].min()
                    existing_end = existing_candles['timestamp'].max()
            except (FileNotFoundError, ValueError):
                pass  # No hay datos existentes, descargar todo
            
            # Determinar qué descargar
            if existing_candles is not None and not existing_candles.empty:
                # Verificar si necesitamos descargar histórico anterior (para cumplir min_window_days)
                window_days = (existing_end - existing_start).days if existing_start and existing_end else 0
                
                if window_days < min_window_days:
                    # Necesitamos más histórico: descargar desde start_time hasta existing_start
                    historical_start = end_time - timedelta(days=min_window_days + 30)
                    if not existing_start or historical_start < existing_start:
                        # Descargar histórico faltante
                        historical_candles = self.fetch_klines_paginated(
                            symbol=symbol,
                            interval=interval,
                            start_time=historical_start,
                            end_time=existing_start
                        )
                        if not historical_candles.empty:
                            # Guardar histórico primero
                            self.candle_repo.save(symbol, interval, historical_candles, merge_existing=True)
                
                # Descargar velas nuevas (desde el último timestamp hasta ahora)
                # Usar un poco antes del existing_end para evitar gaps
                interval_days_map = {
                    "1m": 1/1440, "5m": 5/1440, "15m": 15/1440, "30m": 30/1440,
                    "1h": 1/24, "4h": 4/24, "12h": 12/24,
                    "1d": 1, "1w": 7, "1M": 30
                }
                interval_days = interval_days_map.get(interval, 1)
                fetch_start = existing_end - timedelta(days=interval_days * 2) if existing_end else start_time
                
                candles = self.fetch_klines_paginated(
                    symbol=symbol,
                    interval=interval,
                    start_time=fetch_start,
                    end_time=end_time
                )
            else:
                # Descargar histórico completo
                candles = self.fetch_klines_paginated(
                    symbol=symbol,
                    interval=interval,
                    start_time=start_time,
                    end_time=end_time
                )
            
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
            
            # Verificar si cumplimos con la ventana mínima
            if not merged_candles.empty:
                window_days = (merged_candles['timestamp'].max() - merged_candles['timestamp'].min()).days
                if window_days < min_window_days:
                    warnings.append(f"Window is {window_days} days (minimum: {min_window_days} days)")
            
            return {
                "success": True,
                "symbol": symbol,
                "interval": interval,
                "metadata": metadata,
                "warnings": warnings,
                "validation": validation,
                "downloaded": len(candles),
                "total_after_merge": len(merged_candles) if not merged_candles.empty else 0
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

