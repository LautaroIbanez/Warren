"""Indicadores técnicos para análisis de trading."""
import pandas as pd
import numpy as np
from typing import Optional


def calculate_ema(series: pd.Series, period: int) -> pd.Series:
    """Calcula Exponential Moving Average."""
    return series.ewm(span=period, adjust=False).mean()


def calculate_sma(series: pd.Series, period: int) -> pd.Series:
    """Calcula Simple Moving Average."""
    return series.rolling(window=period).mean()


def calculate_macd(
    series: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9
) -> dict[str, pd.Series]:
    """Calcula MACD (Moving Average Convergence Divergence)."""
    ema_fast = calculate_ema(series, fast)
    ema_slow = calculate_ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = calculate_ema(macd_line, signal)
    histogram = macd_line - signal_line
    
    return {
        "macd": macd_line,
        "signal": signal_line,
        "histogram": histogram
    }


def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Calcula Relative Strength Index."""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_bollinger_bands(
    series: pd.Series,
    period: int = 20,
    std_dev: float = 2.0
) -> dict[str, pd.Series]:
    """Calcula Bollinger Bands."""
    sma = calculate_sma(series, period)
    std = series.rolling(window=period).std()
    
    upper = sma + (std * std_dev)
    lower = sma - (std * std_dev)
    
    return {
        "upper": upper,
        "middle": sma,
        "lower": lower
    }


def calculate_atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14
) -> pd.Series:
    """Calcula Average True Range."""
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    
    return atr


def calculate_momentum(series: pd.Series, period: int = 10) -> pd.Series:
    """Calcula Momentum."""
    return series.diff(period)


def calculate_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula todos los indicadores técnicos y los añade al DataFrame.
    
    Requiere columnas: 'close', 'high', 'low', 'open'
    """
    result = df.copy()
    close = result['close']
    high = result['high']
    low = result['low']
    
    # Moving Averages
    result['ema_12'] = calculate_ema(close, 12)
    result['ema_26'] = calculate_ema(close, 26)
    result['sma_20'] = calculate_sma(close, 20)
    result['sma_50'] = calculate_sma(close, 50)
    
    # MACD
    macd_data = calculate_macd(close)
    result['macd'] = macd_data['macd']
    result['macd_signal'] = macd_data['signal']
    result['macd_histogram'] = macd_data['histogram']
    
    # RSI
    result['rsi'] = calculate_rsi(close, 14)
    
    # Bollinger Bands
    bb_data = calculate_bollinger_bands(close, 20, 2.0)
    result['bb_upper'] = bb_data['upper']
    result['bb_middle'] = bb_data['middle']
    result['bb_lower'] = bb_data['lower']
    
    # ATR
    result['atr'] = calculate_atr(high, low, close, 14)
    
    # Momentum
    result['momentum'] = calculate_momentum(close, 10)
    
    return result

