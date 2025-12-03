"""Configuración de la aplicación."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuración de Warren."""
    
    # Trading
    DEFAULT_SYMBOL: str = "BTCUSDT"
    DEFAULT_INTERVAL: str = "1d"
    
    # Data paths
    DATA_DIR: str = "./data"
    CANDLES_DIR: str = "./data/candles"
    BACKTESTS_DIR: str = "./data/backtests"
    RISK_DIR: str = "./data/risk"
    
    # Binance API
    BINANCE_API_URL: str = "https://api.binance.com/api/v3"
    
    # Risk thresholds
    MIN_TRADES_FOR_RELIABILITY: int = 30
    MIN_WINDOW_DAYS: int = 90
    STALE_CANDLE_HOURS: int = 24
    
    # Risk validation thresholds
    MIN_PROFIT_FACTOR: float = 1.0  # Profit factor mínimo aceptable
    MAX_DRAWDOWN_PCT: float = 50.0  # Drawdown máximo aceptable (%)
    MIN_TOTAL_RETURN_PCT: float = 0.0  # Retorno total mínimo aceptable (%)
    
    # Backtest execution parameters
    INITIAL_CAPITAL: float = 10000.0  # Capital inicial para simulación
    POSITION_SIZE_PCT: float = 10.0  # Porcentaje del capital por posición (10%)
    TRADING_FEE_PCT: float = 0.1  # Fee de trading por operación (0.1% = 0.001)
    SLIPPAGE_PCT: float = 0.05  # Slippage estimado por operación (0.05% = 0.0005)
    
    # Data window requirements
    MIN_DATA_WINDOW_DAYS: int = 730  # 2 años mínimo para velas diarias
    MAX_GAP_DAYS: int = 7  # Máximo gap permitido entre velas (días)
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

