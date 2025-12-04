"""Integration tests for stale cache scenarios."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
import pandas as pd
from datetime import datetime, timedelta
import json
import tempfile
import shutil
from pathlib import Path

from app.main import app
from app.config import settings


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def temp_data_dir():
    """Create temporary data directory."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


class TestStaleCacheScenarios:
    """Integration tests for stale cache handling."""
    
    @patch('app.api.recommendation.CandleRepository')
    @patch('app.api.recommendation.RiskRepository')
    @patch('app.api.recommendation.StrategyEngine')
    def test_recommendation_blocks_on_stale_cache(self, mock_strategy, mock_risk_repo, mock_candle_repo, client):
        """Test that recommendation blocks when cache is stale."""
        # Setup candles
        mock_candles = pd.DataFrame({
            'timestamp': pd.date_range('2022-01-01', periods=100, freq='D'),
            'open': [40000] * 100,
            'high': [41000] * 100,
            'low': [39000] * 100,
            'close': [40000] * 100,
            'volume': [1000000] * 100
        })
        
        mock_candle_instance = Mock()
        mock_candle_instance.load.return_value = (mock_candles, {
            "source_file_hash": "current_hash",
            "as_of": "2022-01-01T00:00:00",
            "from_date": "2022-01-01",
            "to_date": "2022-04-10",
            "window_days": 100
        })
        mock_candle_instance.get_freshness.return_value = {"is_stale": False}
        mock_candle_repo.return_value = mock_candle_instance
        
        # Stale cache validation
        mock_risk_instance = Mock()
        mock_risk_instance.load.return_value = (None, {
            "is_stale": True,
            "is_inconsistent": False,
            "reason": f"Data is stale: {settings.STALE_CANDLE_HOURS + 1.0} hours old (max: {settings.STALE_CANDLE_HOURS}h)",
            "cached_hash": "old_hash",
            "current_hash": "current_hash",
            "cached_as_of": "2021-12-01T00:00:00",
            "current_as_of": "2022-01-01T00:00:00"
        })
        mock_risk_repo.return_value = mock_risk_instance
        
        response = client.get("/recommendation/today")
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_blocked"] is True
        assert data.get("is_stale") is True
        assert "stale" in data.get("stale_reason", "").lower() or "stale" in data.get("block_reason", "").lower()
    
    @patch('app.api.recommendation.CandleRepository')
    @patch('app.api.recommendation.RiskRepository')
    @patch('app.api.recommendation.StrategyEngine')
    def test_recommendation_warns_on_inconsistent_hash(self, mock_strategy, mock_risk_repo, mock_candle_repo, client):
        """Test that recommendation blocks when cache hash doesn't match."""
        mock_candles = pd.DataFrame({
            'timestamp': pd.date_range('2022-01-01', periods=100, freq='D'),
            'open': [40000] * 100,
            'high': [41000] * 100,
            'low': [39000] * 100,
            'close': [40000] * 100,
            'volume': [1000000] * 100
        })
        
        mock_candle_instance = Mock()
        mock_candle_instance.load.return_value = (mock_candles, {
            "source_file_hash": "new_hash_123",
            "as_of": "2022-01-01T00:00:00",
            "from_date": "2022-01-01",
            "to_date": "2022-04-10",
            "window_days": 100
        })
        mock_candle_instance.get_freshness.return_value = {"is_stale": False}
        mock_candle_repo.return_value = mock_candle_instance
        
        # Inconsistent hash
        mock_risk_instance = Mock()
        mock_risk_instance.load.return_value = (None, {
            "is_stale": False,
            "is_inconsistent": True,
            "reason": "Hash mismatch: cached=old_hash_456... vs current=new_hash_123...",
            "cached_hash": "old_hash_456",
            "current_hash": "new_hash_123"
        })
        mock_risk_repo.return_value = mock_risk_instance
        
        response = client.get("/recommendation/today")
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_blocked"] is True
        assert "mismatch" in data.get("block_reason", "").lower() or "inconsistent" in data.get("block_reason", "").lower()
    
    @patch('app.api.recommendation.CandleRepository')
    @patch('app.api.recommendation.RiskRepository')
    @patch('app.api.recommendation.StrategyEngine')
    def test_recommendation_passes_with_fresh_cache(self, mock_strategy, mock_risk_repo, mock_candle_repo, client):
        """Test that recommendation passes when cache is fresh and valid."""
        mock_candles = pd.DataFrame({
            'timestamp': pd.date_range('2022-01-01', periods=100, freq='D'),
            'open': [40000] * 100,
            'high': [41000] * 100,
            'low': [39000] * 100,
            'close': [40000] * 100,
            'volume': [1000000] * 100
        })
        
        test_hash = "fresh_hash_789"
        test_timestamp = "2022-01-01T00:00:00"
        
        mock_candle_instance = Mock()
        mock_candle_instance.load.return_value = (mock_candles, {
            "source_file_hash": test_hash,
            "as_of": test_timestamp,
            "from_date": "2022-01-01",
            "to_date": "2022-04-10",
            "window_days": 100
        })
        mock_candle_instance.get_freshness.return_value = {"is_stale": False}
        mock_candle_repo.return_value = mock_candle_instance
        
        # Fresh cache with good metrics
        mock_risk_data = {
            "metrics": {
                "total_trades": settings.MIN_TRADES_FOR_RELIABILITY + 10,
                "profit_factor": settings.MIN_PROFIT_FACTOR + 0.5,
                "total_return": 15.0,
                "max_drawdown": 20.0,
                "is_reliable": True
            },
            "validation": {
                "trade_count": settings.MIN_TRADES_FOR_RELIABILITY + 10,
                "is_reliable": True
            }
        }
        
        mock_risk_instance = Mock()
        mock_risk_instance.load.return_value = (mock_risk_data, {
            "is_stale": False,
            "is_inconsistent": False,
            "reason": "Cache is valid",
            "cached_hash": test_hash,
            "current_hash": test_hash,
            "cached_as_of": test_timestamp,
            "current_as_of": test_timestamp
        })
        mock_risk_repo.return_value = mock_risk_instance
        
        # Mock strategy
        mock_strategy_instance = Mock()
        mock_recommendation = Mock()
        mock_recommendation.to_dict.return_value = {
            "signal": "BUY",
            "confidence": 0.8,
            "entry_price": 40000.0,
            "stop_loss": 38000.0,
            "take_profit": 42000.0,
            "rationale": "Strong signal"
        }
        mock_strategy_instance.generate_recommendation.return_value = mock_recommendation
        mock_strategy.return_value = mock_strategy_instance
        
        response = client.get("/recommendation/today")
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("is_blocked") is not True
        assert data["signal"] in ["BUY", "SELL", "HOLD"]
        assert data.get("candles_hash") == test_hash
    
    @patch('app.api.risk.RiskRepository')
    @patch('app.api.risk.BacktestRepository')
    @patch('app.api.risk.CandleRepository')
    def test_risk_endpoint_recomputes_on_stale_cache(self, mock_candle_repo, mock_backtest_repo, mock_risk_repo, client):
        """Test that risk endpoint recomputes when cache is stale."""
        test_hash = "test_hash"
        test_timestamp = "2022-01-01T00:00:00"
        
        # Setup candle repo
        mock_candle_instance = Mock()
        mock_candle_instance.load.return_value = (None, {
            "source_file_hash": test_hash,
            "as_of": test_timestamp,
            "from_date": "2022-01-01",
            "to_date": "2022-04-10",
            "window_days": 100
        })
        mock_candle_repo.return_value = mock_candle_instance
        
        # Stale cache
        mock_risk_instance = Mock()
        mock_risk_instance.load.return_value = (None, {
            "is_stale": True,
            "is_inconsistent": False,
            "reason": "Data is stale: 25.0 hours old"
        })
        mock_risk_repo.return_value = mock_risk_instance
        
        # Backtest data for recomputation
        mock_backtest_data = {
            "trades": [{"entry_time": "2022-01-01", "pnl": 100.0}],
            "metrics": {
                "total_trades": 30,
                "profit_factor": 1.5,
                "total_return": 10.0,
                "max_drawdown": 15.0,
                "is_reliable": True
            }
        }
        
        mock_backtest_instance = Mock()
        mock_backtest_instance.load.return_value = (mock_backtest_data, {
            "is_stale": False,
            "is_inconsistent": False
        })
        mock_backtest_repo.return_value = mock_backtest_instance
        
        response = client.get("/risk/metrics")
        
        assert response.status_code == 200
        data = response.json()
        # Should recompute from backtest
        assert data["cache_info"]["computed"] is True
        assert data["cache_info"]["was_recomputed"] is True

