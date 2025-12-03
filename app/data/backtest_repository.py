"""Repositorio de backtests basado en archivos JSON."""
import json
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime
import hashlib
import logging
import pandas as pd

logger = logging.getLogger(__name__)

from app.config import settings
from app.core.backtest import BacktestResult


class BacktestRepository:
    """Repositorio para almacenar y cargar resultados de backtests."""
    
    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = Path(data_dir or settings.BACKTESTS_DIR)
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_file_path(self, symbol: str, interval: str) -> Path:
        """Obtiene la ruta del archivo para un símbolo/intervalo."""
        filename = f"{symbol}_{interval}.json"
        return self.data_dir / filename
    
    def _calculate_hash(self, candles_hash: str, timestamp: str) -> str:
        """Calcula hash para identificar backtest."""
        content = f"{candles_hash}_{timestamp}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def save(
        self,
        symbol: str,
        interval: str,
        result: BacktestResult,
        candles_hash: Optional[str] = None,
        candles_timestamp: Optional[str] = None
    ) -> dict:
        """
        Guarda resultado de backtest en JSON.
        
        Args:
            symbol: Símbolo del par
            interval: Intervalo
            result: BacktestResult a guardar
            candles_hash: Hash de las velas usadas (opcional)
            candles_timestamp: Timestamp de las velas (opcional)
        
        Returns:
            Dict con metadata del archivo guardado
        """
        file_path = self._get_file_path(symbol, interval)
        
        # Preparar datos para JSON
        data = result.to_dict()
        
        # Añadir metadata
        data['metadata'] = {
            "symbol": symbol,
            "interval": interval,
            "saved_at": datetime.now().isoformat(),
            "candles_hash": candles_hash,
            "candles_timestamp": candles_timestamp,
            "backtest_hash": self._calculate_hash(
                candles_hash or "unknown",
                candles_timestamp or datetime.now().isoformat()
            )
        }
        
        # Guardar JSON
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return {
            "file_path": str(file_path),
            "saved_at": data['metadata']['saved_at'],
            "backtest_hash": data['metadata']['backtest_hash']
        }
    
    def load(
        self,
        symbol: str,
        interval: str,
        candles_hash: Optional[str] = None,
        candles_as_of: Optional[str] = None
    ) -> Tuple[Optional[dict], dict]:
        """
        Carga resultado de backtest desde JSON, validando frescura y coherencia.
        
        Args:
            symbol: Símbolo del par
            interval: Intervalo
            candles_hash: Hash actual de velas (para validación)
            candles_as_of: Timestamp actual de velas (para validación)
        
        Returns:
            Tuple (data_dict, validation_info)
            - data_dict: Datos del backtest o None si no existe/está obsoleto
            - validation_info: Dict con is_stale, is_inconsistent, reason
        """
        file_path = self._get_file_path(symbol, interval)
        
        validation_info = {
            "is_stale": False,
            "is_inconsistent": False,
            "reason": None,
            "cached_hash": None,
            "current_hash": candles_hash,
            "cached_as_of": None,
            "current_as_of": candles_as_of
        }
        
        if not file_path.exists():
            validation_info["reason"] = "Backtest file does not exist"
            return None, validation_info
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Obtener metadata del cache
            metadata = data.get('metadata', {})
            cached_hash = metadata.get('candles_hash')
            cached_as_of = metadata.get('candles_timestamp')
            saved_at = metadata.get('saved_at')
            
            validation_info["cached_hash"] = cached_hash
            validation_info["cached_as_of"] = cached_as_of
            
            # Validar coherencia de hash
            if candles_hash and cached_hash:
                if cached_hash != candles_hash:
                    validation_info["is_inconsistent"] = True
                    validation_info["reason"] = f"Hash mismatch: cached={cached_hash[:8]}... vs current={candles_hash[:8]}..."
                    return None, validation_info
            
            # Validar frescura temporal
            if candles_as_of and cached_as_of:
                if cached_as_of != candles_as_of:
                    validation_info["is_inconsistent"] = True
                    validation_info["reason"] = f"Timestamp mismatch: cached={cached_as_of} vs current={candles_as_of}"
                    return None, validation_info
                
                # Validar que no esté stale (más de STALE_CANDLE_HOURS)
                try:
                    cached_time = pd.to_datetime(cached_as_of)
                    current_time = pd.Timestamp.now(tz=cached_time.tz) if cached_time.tz else pd.Timestamp.now()
                    hours_old = (current_time - cached_time).total_seconds() / 3600
                    
                    if hours_old > settings.STALE_CANDLE_HOURS:
                        validation_info["is_stale"] = True
                        validation_info["reason"] = f"Data is stale: {hours_old:.1f} hours old (max: {settings.STALE_CANDLE_HOURS}h)"
                        return None, validation_info
                except Exception:
                    pass  # Si falla parsing, continuar
            
            # Cache válido
            validation_info["reason"] = "Cache is valid"
            return data, validation_info
            
        except json.JSONDecodeError as e:
            logger.warning(f"Backtest file {file_path} is corrupt: {str(e)}")
            validation_info["reason"] = f"File is corrupt: {str(e)}"
            # Eliminar archivo corrupto para permitir regeneración
            try:
                file_path.unlink()
            except Exception:
                pass
            return None, validation_info
        except Exception as e:
            logger.error(f"Error reading backtest file: {str(e)}")
            validation_info["reason"] = f"Error reading file: {str(e)}"
            return None, validation_info
    
    def exists(self, symbol: str, interval: str) -> bool:
        """Verifica si existe archivo para símbolo/intervalo."""
        file_path = self._get_file_path(symbol, interval)
        return file_path.exists()

