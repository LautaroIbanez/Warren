"""Tests for recommendation endpoint blocking logic."""
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
from app.core.backtest import evaluate_risk_for_signal
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


class TestRiskEvaluationFunction:
    """Test the centralized risk evaluation function."""
    
    def test_blocks_on_insufficient_trades(self):
        """Test blocking when total_trades < MIN_TRADES_FOR_RELIABILITY."""
        risk_metrics = {
            "total_trades": settings.MIN_TRADES_FOR_RELIABILITY - 1,
            "profit_factor": 2.0,
            "total_return": 20.0,
            "max_drawdown": 10.0,
            "is_reliable": False
        }
        
        result = evaluate_risk_for_signal(
            risk_metrics=risk_metrics,
            risk_validation={"trade_count": risk_metrics["total_trades"], "is_reliable": False},
            cache_validation=None
        )
        
        assert result["is_blocked"] is True
        assert "Insuficientes trades" in result["block_reason"] or "trades" in result["block_reason"].lower()
    
    def test_blocks_on_low_profit_factor(self):
        """Test blocking when profit_factor < MIN_PROFIT_FACTOR."""
        risk_metrics = {
            "total_trades": settings.MIN_TRADES_FOR_RELIABILITY,
            "profit_factor": settings.MIN_PROFIT_FACTOR - 0.1,
            "total_return": 5.0,
            "max_drawdown": 15.0,
            "is_reliable": False
        }
        
        result = evaluate_risk_for_signal(
            risk_metrics=risk_metrics,
            risk_validation={"trade_count": risk_metrics["total_trades"], "is_reliable": False},
            cache_validation=None
        )
        
        assert result["is_blocked"] is True
        assert "Profit factor" in result["block_reason"] or "profit_factor" in result["block_reason"].lower()
    
    def test_blocks_on_negative_return(self):
        """Test blocking when total_return <= MIN_TOTAL_RETURN_PCT."""
        risk_metrics = {
            "total_trades": settings.MIN_TRADES_FOR_RELIABILITY,
            "profit_factor": 1.2,
            "total_return": -5.0,  # Negative return
            "max_drawdown": 20.0,
            "is_reliable": False
        }
        
        result = evaluate_risk_for_signal(
            risk_metrics=risk_metrics,
            risk_validation={"trade_count": risk_metrics["total_trades"], "is_reliable": False},
            cache_validation=None
        )
        
        assert result["is_blocked"] is True
        assert "Retorno total" in result["block_reason"] or "return" in result["block_reason"].lower()
    
    def test_blocks_on_high_drawdown(self):
        """Test blocking when max_drawdown > MAX_DRAWDOWN_PCT."""
        risk_metrics = {
            "total_trades": settings.MIN_TRADES_FOR_RELIABILITY,
            "profit_factor": 1.5,
            "total_return": 10.0,
            "max_drawdown": settings.MAX_DRAWDOWN_PCT + 10.0,
            "is_reliable": False
        }
        
        result = evaluate_risk_for_signal(
            risk_metrics=risk_metrics,
            risk_validation={"trade_count": risk_metrics["total_trades"], "is_reliable": False},
            cache_validation=None
        )
        
        assert result["is_blocked"] is True
        assert "Drawdown" in result["block_reason"] or "drawdown" in result["block_reason"].lower()
    
    def test_blocks_on_stale_cache(self):
        """Test blocking when cache is stale."""
        cache_validation = {
            "is_stale": True,
            "is_inconsistent": False,
            "reason": "Data is stale: 25.0 hours old (max: 24h)"
        }
        
        result = evaluate_risk_for_signal(
            risk_metrics={"total_trades": 50, "profit_factor": 2.0},
            risk_validation={"is_reliable": True},
            cache_validation=cache_validation
        )
        
        assert result["is_blocked"] is True
        assert result["is_stale"] is True
        assert "stale" in result["block_reason"].lower()
    
    def test_blocks_on_inconsistent_cache(self):
        """Test blocking when cache is inconsistent."""
        cache_validation = {
            "is_stale": False,
            "is_inconsistent": True,
            "reason": "Hash mismatch: cached=abc123... vs current=def456..."
        }
        
        result = evaluate_risk_for_signal(
            risk_metrics={"total_trades": 50, "profit_factor": 2.0},
            risk_validation={"is_reliable": True},
            cache_validation=cache_validation
        )
        
        assert result["is_blocked"] is True
        assert "inconsistent" in result["block_reason"].lower() or "mismatch" in result["block_reason"].lower()
    
    def test_passes_with_good_metrics(self):
        """Test that signal passes when all metrics are good."""
        risk_metrics = {
            "total_trades": settings.MIN_TRADES_FOR_RELIABILITY + 10,
            "profit_factor": settings.MIN_PROFIT_FACTOR + 0.5,
            "total_return": settings.MIN_TOTAL_RETURN_PCT + 5.0,
            "max_drawdown": settings.MAX_DRAWDOWN_PCT - 10.0,
            "is_reliable": True
        }
        
        result = evaluate_risk_for_signal(
            risk_metrics=risk_metrics,
            risk_validation={"trade_count": risk_metrics["total_trades"], "is_reliable": True},
            cache_validation={"is_stale": False, "is_inconsistent": False, "reason": "Cache is valid"}
        )
        
        assert result["is_blocked"] is False
        assert result["block_reason"] is None
    
    def test_returns_multiple_block_reasons(self):
        """Test that multiple failing criteria are all included in block_reasons."""
        risk_metrics = {
            "total_trades": settings.MIN_TRADES_FOR_RELIABILITY - 5,
            "profit_factor": settings.MIN_PROFIT_FACTOR - 0.2,
            "total_return": -10.0,
            "max_drawdown": settings.MAX_DRAWDOWN_PCT + 20.0,
            "is_reliable": False
        }
        
        result = evaluate_risk_for_signal(
            risk_metrics=risk_metrics,
            risk_validation={"trade_count": risk_metrics["total_trades"], "is_reliable": False},
            cache_validation=None
        )
        
        assert result["is_blocked"] is True
        assert len(result["block_reasons"]) >= 2  # Should have multiple reasons


class TestRecommendationEndpoint:
    """Test recommendation endpoint blocking behavior."""
    
    @patch('app.api.recommendation.validate_data_window')
    @patch('app.api.recommendation.validate_gaps')
    @patch('app.api.recommendation.CandleRepository')
    @patch('app.api.recommendation.RiskRepository')
    @patch('app.api.recommendation.StrategyEngine')
    def test_recommendation_blocks_on_poor_metrics(self, mock_strategy, mock_risk_repo, mock_candle_repo, mock_validate_gaps, mock_validate_window, client, temp_data_dir):
        """Test that recommendation endpoint blocks signals when metrics are poor."""
        # Mock validation functions
        mock_validate_window.return_value = (True, None, {"window_days": 800})
        mock_validate_gaps.return_value = (True, [], {})
        
        # Setup mocks
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
            "source_file_hash": "test_hash",
            "as_of": "2022-01-01T00:00:00",
            "from_date": "2022-01-01",
            "to_date": "2022-04-10",
            "window_days": 100
        })
        mock_candle_instance.get_freshness.return_value = {"is_stale": False}
        mock_candle_repo.return_value = mock_candle_instance
        
        # Poor risk metrics
        mock_risk_data = {
            "metrics": {
                "total_trades": settings.MIN_TRADES_FOR_RELIABILITY - 5,
                "profit_factor": settings.MIN_PROFIT_FACTOR - 0.2,
                "total_return": -5.0,
                "max_drawdown": 60.0,
                "is_reliable": False
            },
            "validation": {
                "trade_count": settings.MIN_TRADES_FOR_RELIABILITY - 5,
                "window_days": 100,  # Insufficient window
                "is_reliable": False
            }
        }
        
        mock_risk_instance = Mock()
        mock_risk_instance.load.return_value = (mock_risk_data, {
            "is_stale": False,
            "is_inconsistent": False,
            "reason": "Cache is valid"
        })
        mock_risk_repo.return_value = mock_risk_instance
        
        response = client.get("/recommendation/today")
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_blocked"] is True
        assert data["signal"] == "HOLD"
        assert data["block_reason"] is not None
    
    @patch('app.api.recommendation.validate_data_window')
    @patch('app.api.recommendation.validate_gaps')
    @patch('app.api.recommendation.CandleRepository')
    @patch('app.api.recommendation.RiskRepository')
    @patch('app.api.recommendation.StrategyEngine')
    def test_recommendation_passes_with_good_metrics(self, mock_strategy, mock_risk_repo, mock_candle_repo, mock_validate_gaps, mock_validate_window, client):
        """Test that recommendation endpoint passes signals when metrics are good."""
        # Mock validation functions
        mock_validate_window.return_value = (True, None, {"window_days": 800})
        mock_validate_gaps.return_value = (True, [], {})
        
        # Setup mocks
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
            "source_file_hash": "test_hash",
            "as_of": "2022-01-01T00:00:00",
            "from_date": "2022-01-01",
            "to_date": "2022-04-10",
            "window_days": 100
        })
        mock_candle_instance.get_freshness.return_value = {"is_stale": False}
        mock_candle_repo.return_value = mock_candle_instance
        
        # Good risk metrics
        mock_risk_data = {
            "metrics": {
                "total_trades": settings.MIN_TRADES_FOR_RELIABILITY + 10,
                "profit_factor": settings.MIN_PROFIT_FACTOR + 0.5,
                "total_return": settings.MIN_TOTAL_RETURN_PCT + 10.0,
                "max_drawdown": settings.MAX_DRAWDOWN_PCT - 10.0,
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
            "reason": "Cache is valid"
        })
        mock_risk_repo.return_value = mock_risk_instance
        
        # Mock strategy to return a recommendation
        mock_strategy_instance = Mock()
        mock_recommendation = Mock()
        mock_recommendation.to_dict.return_value = {
            "signal": "BUY",
            "confidence": 0.8,
            "entry_price": 40000.0,
            "stop_loss": 38000.0,
            "take_profit": 42000.0,
            "rationale": "Strong buy signal"
        }
        mock_strategy_instance.generate_recommendation.return_value = mock_recommendation
        mock_strategy.return_value = mock_strategy_instance
        
        response = client.get("/recommendation/today")
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("is_blocked") is not True  # Should not be blocked
        assert data["signal"] in ["BUY", "SELL", "HOLD"]
    
    @patch('app.api.recommendation.validate_data_window')
    @patch('app.api.recommendation.validate_gaps')
    @patch('app.api.recommendation.CandleRepository')
    @patch('app.api.recommendation.RiskRepository')
    def test_recommendation_blocks_on_stale_cache(self, mock_risk_repo, mock_candle_repo, mock_validate_gaps, mock_validate_window, client):
        """Test that recommendation blocks when cache is stale."""
        # Mock validation functions
        mock_validate_window.return_value = (True, None, {"window_days": 800})
        mock_validate_gaps.return_value = (True, [], {})
        
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
            "source_file_hash": "test_hash",
            "as_of": "2022-01-01T00:00:00",
            "from_date": "2022-01-01",
            "to_date": "2022-04-10",
            "window_days": 100
        })
        mock_candle_instance.get_freshness.return_value = {"is_stale": False}
        mock_candle_repo.return_value = mock_candle_instance
        
        # Stale cache
        mock_risk_instance = Mock()
        mock_risk_instance.load.return_value = (None, {
            "is_stale": True,
            "is_inconsistent": False,
            "reason": "Data is stale: 25.0 hours old (max: 24h)"
        })
        mock_risk_repo.return_value = mock_risk_instance
        
        response = client.get("/recommendation/today")
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_blocked"] is True
        assert data.get("is_stale") is True

