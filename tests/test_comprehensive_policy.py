"""Comprehensive integration tests for policy violations and blocking."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import pandas as pd
from datetime import datetime, timedelta

from app.core.backtest import evaluate_risk_for_signal
from app.core.policy import RiskPolicy
from app.config import settings
from app.main import app

client = TestClient(app)


class TestComprehensivePolicyViolations:
    """Comprehensive tests for all policy violation scenarios."""
    
    def test_insufficient_trades_blocks_signal(self):
        """Test that insufficient trades (<30) blocks signal."""
        risk_metrics = {
            "total_trades": 25,
            "profit_factor": 1.5,
            "total_return": 10.0,
            "max_drawdown": 20.0
        }
        
        result = evaluate_risk_for_signal(
            risk_metrics=risk_metrics,
            risk_validation=None,
            cache_validation=None,
            window_days=800
        )
        
        assert result["is_blocked"] is True
        assert len(result["violations"]) == 1
        assert result["violations"][0]["type"] == "insufficient_trades"
        assert "Insuficientes trades" in result["block_reason"]
    
    def test_negative_return_blocks_signal(self):
        """Test that negative return blocks signal."""
        risk_metrics = {
            "total_trades": 50,
            "profit_factor": 1.5,
            "total_return": -5.0,  # Negative return
            "max_drawdown": 20.0
        }
        
        result = evaluate_risk_for_signal(
            risk_metrics=risk_metrics,
            risk_validation=None,
            cache_validation=None,
            window_days=800
        )
        
        assert result["is_blocked"] is True
        violations = [v["type"] for v in result["violations"]]
        assert "negative_return" in violations
    
    def test_zero_return_blocks_signal(self):
        """Test that zero return (<= threshold) blocks signal."""
        risk_metrics = {
            "total_trades": 50,
            "profit_factor": 1.5,
            "total_return": 0.0,  # Zero return
            "max_drawdown": 20.0
        }
        
        result = evaluate_risk_for_signal(
            risk_metrics=risk_metrics,
            risk_validation=None,
            cache_validation=None,
            window_days=800
        )
        
        assert result["is_blocked"] is True
        violations = [v["type"] for v in result["violations"]]
        assert "negative_return" in violations
    
    def test_pf_below_threshold_blocks_signal(self):
        """Test that profit factor below threshold blocks signal."""
        risk_metrics = {
            "total_trades": 50,
            "profit_factor": 0.8,  # Below MIN_PROFIT_FACTOR (1.0)
            "total_return": 10.0,
            "max_drawdown": 20.0
        }
        
        result = evaluate_risk_for_signal(
            risk_metrics=risk_metrics,
            risk_validation=None,
            cache_validation=None,
            window_days=800
        )
        
        assert result["is_blocked"] is True
        violations = [v["type"] for v in result["violations"]]
        assert "low_profit_factor" in violations
    
    def test_excessive_drawdown_blocks_signal(self):
        """Test that excessive drawdown (>50%) blocks signal."""
        risk_metrics = {
            "total_trades": 50,
            "profit_factor": 1.5,
            "total_return": 10.0,
            "max_drawdown": 60.0  # Above MAX_DRAWDOWN_PCT (50%)
        }
        
        result = evaluate_risk_for_signal(
            risk_metrics=risk_metrics,
            risk_validation=None,
            cache_validation=None,
            window_days=800
        )
        
        assert result["is_blocked"] is True
        violations = [v["type"] for v in result["violations"]]
        assert "high_drawdown" in violations
    
    def test_stale_cache_blocks_signal(self):
        """Test that stale cache blocks signal."""
        cache_validation = {
            "is_stale": True,
            "reason": "Data is stale: 25.0 hours old (max: 24h)"
        }
        
        result = evaluate_risk_for_signal(
            risk_metrics=None,
            risk_validation=None,
            cache_validation=cache_validation,
            window_days=None
        )
        
        assert result["is_blocked"] is True
        assert result["is_stale"] is True
        assert "stale" in result["stale_reason"].lower()
    
    def test_insufficient_window_blocks_signal(self):
        """Test that insufficient window (<730 days) blocks signal."""
        risk_metrics = {
            "total_trades": 50,
            "profit_factor": 1.5,
            "total_return": 10.0,
            "max_drawdown": 20.0
        }
        
        result = evaluate_risk_for_signal(
            risk_metrics=risk_metrics,
            risk_validation=None,
            cache_validation=None,
            window_days=100  # Below MIN_DATA_WINDOW_DAYS (730)
        )
        
        assert result["is_blocked"] is True
        violations = [v["type"] for v in result["violations"]]
        assert "insufficient_window" in violations
    
    def test_multiple_violations_all_reported(self):
        """Test that multiple violations are all reported."""
        risk_metrics = {
            "total_trades": 10,  # Insufficient
            "profit_factor": 0.5,  # Below threshold
            "total_return": -5.0,  # Negative
            "max_drawdown": 60.0  # Excessive
        }
        
        result = evaluate_risk_for_signal(
            risk_metrics=risk_metrics,
            risk_validation=None,
            cache_validation=None,
            window_days=100  # Insufficient window
        )
        
        assert result["is_blocked"] is True
        assert len(result["violations"]) == 5  # All violations
        violation_types = {v["type"] for v in result["violations"]}
        assert violation_types == {
            "insufficient_trades",
            "insufficient_window",
            "low_profit_factor",
            "negative_return",
            "high_drawdown"
        }
    
    def test_good_metrics_pass(self):
        """Test that good metrics pass all checks."""
        risk_metrics = {
            "total_trades": 50,
            "profit_factor": 1.5,
            "total_return": 10.0,
            "max_drawdown": 20.0
        }
        
        result = evaluate_risk_for_signal(
            risk_metrics=risk_metrics,
            risk_validation=None,
            cache_validation=None,
            window_days=800
        )
        
        assert result["is_blocked"] is False
        assert len(result["violations"]) == 0


class TestPolicyViolationMessages:
    """Test that violation messages are clear and actionable."""
    
    def test_insufficient_trades_message(self):
        """Test insufficient trades message includes actual and required values."""
        violation = RiskPolicy.check_trades(10)
        assert violation is not None
        assert str(settings.MIN_TRADES_FOR_RELIABILITY) in violation.message
        assert "10" in violation.message or str(violation.actual_value) in violation.message
    
    def test_negative_return_message(self):
        """Test negative return message includes actual and threshold values."""
        violation = RiskPolicy.check_total_return(-5.0)
        assert violation is not None
        assert "-5.00" in violation.message or "-5.0" in violation.message
        assert str(settings.MIN_TOTAL_RETURN_PCT) in violation.message
    
    def test_pf_below_threshold_message(self):
        """Test profit factor message includes actual and threshold values."""
        violation = RiskPolicy.check_profit_factor(0.5)
        assert violation is not None
        assert "0.50" in violation.message or "0.5" in violation.message
        assert str(settings.MIN_PROFIT_FACTOR) in violation.message
    
    def test_excessive_drawdown_message(self):
        """Test excessive drawdown message includes actual and threshold values."""
        violation = RiskPolicy.check_max_drawdown(60.0)
        assert violation is not None
        assert "60.00" in violation.message or "60.0" in violation.message
        assert str(settings.MAX_DRAWDOWN_PCT) in violation.message
    
    def test_insufficient_window_message(self):
        """Test insufficient window message includes actual and required values."""
        violation = RiskPolicy.check_window_days(100)
        assert violation is not None
        assert str(settings.MIN_DATA_WINDOW_DAYS) in violation.message
        assert "100" in violation.message or str(violation.actual_value) in violation.message

