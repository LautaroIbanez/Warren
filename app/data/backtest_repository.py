"""Repositorio de backtests basado en archivos JSON."""
import json
from pathlib import Path
from typing import Optional
from datetime import datetime
import hashlib
import logging

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
        interval: str
    ) -> Optional[dict]:
        """
        Carga resultado de backtest desde JSON.
        
        Args:
            symbol: Símbolo del par
            interval: Intervalo
        
        Returns:
            Dict con datos del backtest o None si no existe
        """
        file_path = self._get_file_path(symbol, interval)
        
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        except json.JSONDecodeError as e:
            logger.warning(f"Backtest file {file_path} is corrupt: {str(e)}")
            # Eliminar archivo corrupto para permitir regeneración
            try:
                file_path.unlink()
            except Exception:
                pass
            return None
        except Exception as e:
            logger.error(f"Error reading backtest file: {str(e)}")
            return None
    
    def exists(self, symbol: str, interval: str) -> bool:
        """Verifica si existe archivo para símbolo/intervalo."""
        file_path = self._get_file_path(symbol, interval)
        return file_path.exists()

