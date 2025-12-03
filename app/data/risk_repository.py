"""Repositorio de métricas de riesgo basado en archivos JSON."""
import json
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime
import pandas as pd

from app.config import settings


class RiskRepository:
    """Repositorio para almacenar y cargar métricas de riesgo."""
    
    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = Path(data_dir or settings.RISK_DIR)
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_file_path(self, symbol: str, interval: str) -> Path:
        """Obtiene la ruta del archivo para un símbolo/intervalo."""
        filename = f"{symbol}_{interval}.json"
        return self.data_dir / filename
    
    def save(
        self,
        symbol: str,
        interval: str,
        metrics: dict,
        trade_count: int,
        window_days: int,
        candles_hash: Optional[str] = None,
        candles_as_of: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None
    ) -> dict:
        """
        Guarda métricas de riesgo en JSON con metadata de velas para invalidación.
        
        Args:
            symbol: Símbolo del par
            interval: Intervalo
            metrics: Dict con métricas de riesgo
            trade_count: Número de trades usados
            window_days: Días de lookback
            candles_hash: Hash de las velas usadas (para invalidación)
            candles_as_of: Timestamp de las velas (para invalidación)
            from_date: Fecha inicial del período
            to_date: Fecha final del período
        
        Returns:
            Dict con metadata del archivo guardado
        """
        file_path = self._get_file_path(symbol, interval)
        
        # Preparar datos
        data = {
            "symbol": symbol,
            "interval": interval,
            "metrics": metrics,
            "validation": {
                "trade_count": trade_count,
                "window_days": window_days,
                "min_trades_required": settings.MIN_TRADES_FOR_RELIABILITY,
                "min_window_days": settings.MIN_WINDOW_DAYS,
                "is_reliable": metrics.get("is_reliable", False)
            },
            "data_window": {
                "from_date": from_date,
                "to_date": to_date,
                "window_days": window_days
            },
            "candles_metadata": {
                "hash": candles_hash,
                "as_of": candles_as_of
            },
            "saved_at": datetime.now().isoformat()
        }
        
        # Guardar JSON
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return {
            "file_path": str(file_path),
            "saved_at": data["saved_at"]
        }
    
    def load(
        self,
        symbol: str,
        interval: str,
        candles_hash: Optional[str] = None,
        candles_as_of: Optional[str] = None
    ) -> Tuple[Optional[dict], dict]:
        """
        Carga métricas de riesgo desde JSON, validando frescura y coherencia.
        
        Args:
            symbol: Símbolo del par
            interval: Intervalo
            candles_hash: Hash actual de velas (para validación)
            candles_as_of: Timestamp actual de velas (para validación)
        
        Returns:
            Tuple (data_dict, validation_info)
            - data_dict: Datos de riesgo o None si no existe/está obsoleto
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
            validation_info["reason"] = "Risk file does not exist"
            return None, validation_info
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Obtener metadata del cache
            candles_metadata = data.get("candles_metadata", {})
            stored_hash = candles_metadata.get("hash")
            stored_as_of = candles_metadata.get("as_of")
            saved_at = data.get("saved_at")
            
            validation_info["cached_hash"] = stored_hash
            validation_info["cached_as_of"] = stored_as_of
            
            # Validar coherencia de hash
            if candles_hash and stored_hash:
                if stored_hash != candles_hash:
                    validation_info["is_inconsistent"] = True
                    validation_info["reason"] = f"Hash mismatch: cached={stored_hash[:8] if stored_hash else 'none'}... vs current={candles_hash[:8] if candles_hash else 'none'}..."
                    return None, validation_info
            
            # Validar frescura temporal
            if candles_as_of and stored_as_of:
                if stored_as_of != candles_as_of:
                    validation_info["is_inconsistent"] = True
                    validation_info["reason"] = f"Timestamp mismatch: cached={stored_as_of} vs current={candles_as_of}"
                    return None, validation_info
                
                # Validar que no esté stale (más de STALE_CANDLE_HOURS)
                try:
                    cached_time = pd.to_datetime(stored_as_of)
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
            
        except Exception as e:
            validation_info["reason"] = f"Error reading file: {str(e)}"
            raise ValueError(f"Error reading risk file: {str(e)}")
    
    def exists(self, symbol: str, interval: str) -> bool:
        """Verifica si existe archivo para símbolo/intervalo."""
        file_path = self._get_file_path(symbol, interval)
        return file_path.exists()

