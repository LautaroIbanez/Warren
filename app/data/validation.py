"""Validación de datos y ventanas temporales."""
from typing import Optional, Tuple
import pandas as pd

from app.config import settings


def validate_data_window(
    candles: pd.DataFrame,
    min_window_days: Optional[int] = None
) -> Tuple[bool, Optional[str], dict]:
    """
    Valida que las velas cumplan con la ventana temporal mínima.
    
    Args:
        candles: DataFrame con velas
        min_window_days: Días mínimos requeridos (default: config)
    
    Returns:
        Tuple (is_valid, error_message, metadata)
    """
    min_window_days = min_window_days or settings.MIN_DATA_WINDOW_DAYS
    
    if candles.empty:
        return False, "No candles available", {}
    
    # Calcular ventana temporal
    earliest = candles['timestamp'].min()
    latest = candles['timestamp'].max()
    window_days = (latest - earliest).days
    
    metadata = {
        "from_date": earliest.isoformat() if pd.notna(earliest) else None,
        "to_date": latest.isoformat() if pd.notna(latest) else None,
        "window_days": window_days,
        "rows": len(candles),
        "min_required_days": min_window_days
    }
    
    if window_days < min_window_days:
        return False, f"Insufficient data window: {window_days} days (minimum: {min_window_days} days)", metadata
    
    return True, None, metadata


def validate_gaps(
    candles: pd.DataFrame,
    interval: str,
    max_gap_days: Optional[int] = None
) -> Tuple[bool, list, dict]:
    """
    Valida gaps en las velas.
    
    Args:
        candles: DataFrame con velas ordenadas por timestamp
        interval: Intervalo de tiempo (1d, 1h, etc.)
        max_gap_days: Máximo gap permitido en días (default: config)
    
    Returns:
        Tuple (is_valid, gaps_list, metadata)
    """
    max_gap_days = max_gap_days or settings.MAX_GAP_DAYS
    
    if len(candles) < 2:
        return True, [], {"gaps_found": 0}
    
    # Calcular intervalo esperado en días
    interval_days_map = {
        "1m": 1/1440, "5m": 5/1440, "15m": 15/1440, "30m": 30/1440,
        "1h": 1/24, "4h": 4/24, "12h": 12/24,
        "1d": 1, "1w": 7, "1M": 30
    }
    expected_interval_days = interval_days_map.get(interval, 1)
    max_gap_interval = max_gap_days / expected_interval_days  # En número de intervalos
    
    gaps = []
    for i in range(1, len(candles)):
        time_diff = (candles.iloc[i]['timestamp'] - candles.iloc[i-1]['timestamp']).total_seconds() / 86400
        if time_diff > expected_interval_days * max_gap_interval:
            gaps.append({
                "from": candles.iloc[i-1]['timestamp'].isoformat(),
                "to": candles.iloc[i]['timestamp'].isoformat(),
                "gap_days": round(time_diff, 2),
                "expected_interval_days": expected_interval_days
            })
    
    is_valid = len(gaps) == 0 or all(gap['gap_days'] <= max_gap_days for gap in gaps)
    
    return is_valid, gaps, {
        "gaps_found": len(gaps),
        "max_gap_days": max_gap_days
    }


def validate_data_quality(
    candles: pd.DataFrame,
    interval: str,
    min_window_days: Optional[int] = None
) -> dict:
    """
    Validación completa de calidad de datos.
    
    Returns:
        Dict con status, errors, warnings, metadata
    """
    result = {
        "is_valid": False,
        "status": "INSUFFICIENT_DATA",
        "errors": [],
        "warnings": [],
        "metadata": {}
    }
    
    # Validar ventana temporal
    is_valid_window, window_error, window_metadata = validate_data_window(candles, min_window_days)
    result["metadata"].update(window_metadata)
    
    if not is_valid_window:
        result["errors"].append(window_error)
        result["status"] = "INSUFFICIENT_DATA"
        return result
    
    # Validar gaps
    is_valid_gaps, gaps, gaps_metadata = validate_gaps(candles, interval)
    result["metadata"].update(gaps_metadata)
    
    if gaps:
        result["warnings"].append(f"Found {len(gaps)} gaps in data")
        result["metadata"]["gaps"] = gaps
    
    # Verificar duplicados
    duplicates = candles[candles.duplicated(subset=['timestamp'], keep=False)]
    if not duplicates.empty:
        result["warnings"].append(f"Found {len(duplicates)} duplicate timestamps")
    
    # Verificar valores nulos
    null_counts = candles.isnull().sum()
    if null_counts.any():
        null_cols = null_counts[null_counts > 0].to_dict()
        result["warnings"].append(f"Found null values: {null_cols}")
    
    result["is_valid"] = True
    result["status"] = "OK" if not result["warnings"] else "WARNINGS"
    
    return result

