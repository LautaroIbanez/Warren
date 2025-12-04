"""Tests for risk repository reliability calculation with window_days."""
import pytest
from datetime import datetime
from app.data.risk_repository import RiskRepository
from app.config import settings


class TestRiskRepositoryReliability:
    """Test that reliability flag considers both metrics and window_days."""
    
    def test_reliable_with_sufficient_window(self, temp_data_dir):
        """Test that reliability is True when both metrics and window are sufficient."""
        repo = RiskRepository()
        metrics = {
            "total_trades": 50,
            "profit_factor": 1.5,
            "total_return": 10.0,
            "max_drawdown": 20.0,
            "is_reliable": True  # Metrics-based reliability
        }
        
        # Use current timestamp to avoid staleness checks
        current_time = datetime.now().isoformat()
        
        repo.save(
            symbol="BTCUSDT",
            interval="1d",
            metrics=metrics,
            trade_count=50,
            window_days=800,  # Sufficient window
            candles_hash="test_hash",
            candles_as_of=current_time
        )
        
        # Load and check validation (pass None to skip staleness check, or use same timestamp)
        data, _ = repo.load("BTCUSDT", "1d", "test_hash", current_time)
        assert data is not None
        assert data["validation"]["is_reliable"] is True
        assert data["validation"]["window_days"] == 800
    
    def test_unreliable_with_insufficient_window(self, temp_data_dir):
        """Test that reliability is False when window is insufficient even if metrics are good."""
        repo = RiskRepository()
        metrics = {
            "total_trades": 50,
            "profit_factor": 1.5,
            "total_return": 10.0,
            "max_drawdown": 20.0,
            "is_reliable": True  # Metrics-based reliability
        }
        
        # Use current timestamp to avoid staleness checks
        current_time = datetime.now().isoformat()
        
        repo.save(
            symbol="BTCUSDT",
            interval="1d",
            metrics=metrics,
            trade_count=50,
            window_days=100,  # Insufficient window
            candles_hash="test_hash",
            candles_as_of=current_time
        )
        
        # Load and check validation
        data, _ = repo.load("BTCUSDT", "1d", "test_hash", current_time)
        assert data is not None
        # Overall reliability should be False due to insufficient window
        assert data["validation"]["is_reliable"] is False
        assert data["validation"]["window_days"] == 100
        assert data["validation"]["min_window_days"] == settings.MIN_DATA_WINDOW_DAYS
    
    def test_unreliable_with_bad_metrics_and_sufficient_window(self, temp_data_dir):
        """Test that reliability is False when metrics are bad even if window is sufficient."""
        repo = RiskRepository()
        metrics = {
            "total_trades": 10,
            "profit_factor": 0.5,
            "total_return": -5.0,
            "max_drawdown": 60.0,
            "is_reliable": False  # Metrics-based reliability
        }
        
        # Use current timestamp to avoid staleness checks
        current_time = datetime.now().isoformat()
        
        repo.save(
            symbol="BTCUSDT",
            interval="1d",
            metrics=metrics,
            trade_count=10,
            window_days=800,  # Sufficient window
            candles_hash="test_hash",
            candles_as_of=current_time
        )
        
        # Load and check validation
        data, _ = repo.load("BTCUSDT", "1d", "test_hash", current_time)
        assert data is not None
        # Overall reliability should be False due to bad metrics
        assert data["validation"]["is_reliable"] is False
    
    def test_unreliable_with_both_insufficient(self, temp_data_dir):
        """Test that reliability is False when both metrics and window are insufficient."""
        repo = RiskRepository()
        metrics = {
            "total_trades": 10,
            "profit_factor": 0.5,
            "total_return": -5.0,
            "max_drawdown": 60.0,
            "is_reliable": False  # Metrics-based reliability
        }
        
        # Use current timestamp to avoid staleness checks
        current_time = datetime.now().isoformat()
        
        repo.save(
            symbol="BTCUSDT",
            interval="1d",
            metrics=metrics,
            trade_count=10,
            window_days=100,  # Insufficient window
            candles_hash="test_hash",
            candles_as_of=current_time
        )
        
        # Load and check validation
        data, _ = repo.load("BTCUSDT", "1d", "test_hash", current_time)
        assert data is not None
        # Overall reliability should be False
        assert data["validation"]["is_reliable"] is False

