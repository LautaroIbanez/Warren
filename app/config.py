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
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

