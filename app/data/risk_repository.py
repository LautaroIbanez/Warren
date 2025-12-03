"""Repositorio de métricas de riesgo basado en archivos JSON."""
import json
from pathlib import Path
from typing import Optional
from datetime import datetime

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
        window_days: int
    ) -> dict:
        """
        Guarda métricas de riesgo en JSON.
        
        Args:
            symbol: Símbolo del par
            interval: Intervalo
            metrics: Dict con métricas de riesgo
            trade_count: Número de trades usados
            window_days: Días de lookback
        
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
                "is_reliable": trade_count >= settings.MIN_TRADES_FOR_RELIABILITY and window_days >= settings.MIN_WINDOW_DAYS
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
        interval: str
    ) -> Optional[dict]:
        """
        Carga métricas de riesgo desde JSON.
        
        Args:
            symbol: Símbolo del par
            interval: Intervalo
        
        Returns:
            Dict con datos de riesgo o None si no existe
        """
        file_path = self._get_file_path(symbol, interval)
        
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        except Exception as e:
            raise ValueError(f"Error reading risk file: {str(e)}")
    
    def exists(self, symbol: str, interval: str) -> bool:
        """Verifica si existe archivo para símbolo/intervalo."""
        file_path = self._get_file_path(symbol, interval)
        return file_path.exists()

