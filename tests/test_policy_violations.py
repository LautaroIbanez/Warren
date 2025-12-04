"""Tests for risk policy violations."""
import pytest
from app.core.policy import RiskPolicy, PolicyViolation
from app.core.backtest import evaluate_risk_for_signal
from app.config import settings


class TestPolicyViolations:
    """Test individual policy violation checks."""
    
    def test_check_trades_insufficient(self):
        """Test that insufficient trades generates a violation."""
        violation = RiskPolicy.check_trades(10)
        assert violation is not None
        assert violation.type == "insufficient_trades"
        assert violation.actual_value == 10.0
        assert violation.threshold_value == float(settings.MIN_TRADES_FOR_RELIABILITY)
        assert "Insuficientes trades" in violation.message
    
    def test_check_trades_sufficient(self):
        """Test that sufficient trades returns None."""
        violation = RiskPolicy.check_trades(30)
        assert violation is None
    
    def test_check_window_days_insufficient(self):
        """Test that insufficient window days generates a violation."""
        violation = RiskPolicy.check_window_days(100)
        assert violation is not None
        assert violation.type == "insufficient_window"
        assert violation.actual_value == 100.0
        assert violation.threshold_value == float(settings.MIN_DATA_WINDOW_DAYS)
        assert "Ventana de datos insuficiente" in violation.message
    
    def test_check_window_days_sufficient(self):
        """Test that sufficient window days returns None."""
        violation = RiskPolicy.check_window_days(730)
        assert violation is None
    
    def test_check_profit_factor_low(self):
        """Test that low profit factor generates a violation."""
        violation = RiskPolicy.check_profit_factor(0.5)
        assert violation is not None
        assert violation.type == "low_profit_factor"
        assert violation.actual_value == 0.5
        assert violation.threshold_value == float(settings.MIN_PROFIT_FACTOR)
        assert "Profit factor insuficiente" in violation.message
    
    def test_check_profit_factor_sufficient(self):
        """Test that sufficient profit factor returns None."""
        violation = RiskPolicy.check_profit_factor(1.5)
        assert violation is None
    
    def test_check_profit_factor_infinity(self):
        """Test that infinity profit factor returns None (always acceptable)."""
        violation = RiskPolicy.check_profit_factor(float('inf'))
        assert violation is None
    
    def test_check_profit_factor_very_large(self):
        """Test that very large profit factor (representing infinity) returns None."""
        violation = RiskPolicy.check_profit_factor(1e11)
        assert violation is None
    
    def test_check_profit_factor_none(self):
        """Test that None profit factor generates a violation."""
        violation = RiskPolicy.check_profit_factor(None)
        assert violation is not None
        assert violation.type == "low_profit_factor"
        assert violation.actual_value is None
        assert "Profit factor no disponible" in violation.message
    
    def test_check_total_return_negative(self):
        """Test that negative/zero return generates a violation."""
        violation = RiskPolicy.check_total_return(-5.0)
        assert violation is not None
        assert violation.type == "negative_return"
        assert violation.actual_value == -5.0
        assert violation.threshold_value == float(settings.MIN_TOTAL_RETURN_PCT)
        assert "Retorno total insuficiente" in violation.message
    
    def test_check_total_return_zero(self):
        """Test that zero return generates a violation (<= threshold)."""
        violation = RiskPolicy.check_total_return(0.0)
        assert violation is not None
        assert violation.type == "negative_return"
    
    def test_check_total_return_positive(self):
        """Test that positive return returns None."""
        violation = RiskPolicy.check_total_return(5.0)
        assert violation is None
    
    def test_check_max_drawdown_high(self):
        """Test that high drawdown generates a violation."""
        violation = RiskPolicy.check_max_drawdown(60.0)
        assert violation is not None
        assert violation.type == "high_drawdown"
        assert violation.actual_value == 60.0
        assert violation.threshold_value == float(settings.MAX_DRAWDOWN_PCT)
        assert "Drawdown máximo excedido" in violation.message
    
    def test_check_max_drawdown_acceptable(self):
        """Test that acceptable drawdown returns None."""
        violation = RiskPolicy.check_max_drawdown(30.0)
        assert violation is None


class TestPolicyEvaluateAll:
    """Test combined policy evaluation."""
    
    def test_evaluate_all_no_violations(self):
        """Test evaluation with all metrics passing."""
        violations = RiskPolicy.evaluate_all(
            total_trades=50,
            window_days=800,
            profit_factor=1.5,
            total_return=10.0,
            max_drawdown=20.0
        )
        assert len(violations) == 0
    
    def test_evaluate_all_insufficient_trades(self):
        """Test evaluation with insufficient trades."""
        violations = RiskPolicy.evaluate_all(
            total_trades=10,
            window_days=800,
            profit_factor=1.5,
            total_return=10.0,
            max_drawdown=20.0
        )
        assert len(violations) == 1
        assert violations[0].type == "insufficient_trades"
    
    def test_evaluate_all_insufficient_window(self):
        """Test evaluation with insufficient window."""
        violations = RiskPolicy.evaluate_all(
            total_trades=50,
            window_days=100,
            profit_factor=1.5,
            total_return=10.0,
            max_drawdown=20.0
        )
        assert len(violations) == 1
        assert violations[0].type == "insufficient_window"
    
    def test_evaluate_all_low_profit_factor(self):
        """Test evaluation with low profit factor."""
        violations = RiskPolicy.evaluate_all(
            total_trades=50,
            window_days=800,
            profit_factor=0.5,
            total_return=10.0,
            max_drawdown=20.0
        )
        assert len(violations) == 1
        assert violations[0].type == "low_profit_factor"
    
    def test_evaluate_all_negative_return(self):
        """Test evaluation with negative return."""
        violations = RiskPolicy.evaluate_all(
            total_trades=50,
            window_days=800,
            profit_factor=1.5,
            total_return=-5.0,
            max_drawdown=20.0
        )
        assert len(violations) == 1
        assert violations[0].type == "negative_return"
    
    def test_evaluate_all_high_drawdown(self):
        """Test evaluation with high drawdown."""
        violations = RiskPolicy.evaluate_all(
            total_trades=50,
            window_days=800,
            profit_factor=1.5,
            total_return=10.0,
            max_drawdown=60.0
        )
        assert len(violations) == 1
        assert violations[0].type == "high_drawdown"
    
    def test_evaluate_all_multiple_violations(self):
        """Test evaluation with multiple violations."""
        violations = RiskPolicy.evaluate_all(
            total_trades=10,
            window_days=100,
            profit_factor=0.5,
            total_return=-5.0,
            max_drawdown=60.0
        )
        assert len(violations) == 5
        violation_types = {v.type for v in violations}
        assert violation_types == {
            "insufficient_trades",
            "insufficient_window",
            "low_profit_factor",
            "negative_return",
            "high_drawdown"
        }
    
    def test_evaluate_all_profit_factor_infinity(self):
        """Test evaluation with infinity profit factor (should pass)."""
        violations = RiskPolicy.evaluate_all(
            total_trades=50,
            window_days=800,
            profit_factor=float('inf'),
            total_return=10.0,
            max_drawdown=20.0
        )
        # Infinity profit factor should not generate a violation
        pf_violations = [v for v in violations if v.type == "low_profit_factor"]
        assert len(pf_violations) == 0
    
    def test_evaluate_all_window_days_none(self):
        """Test evaluation when window_days is None (should skip window check)."""
        violations = RiskPolicy.evaluate_all(
            total_trades=50,
            window_days=None,
            profit_factor=1.5,
            total_return=10.0,
            max_drawdown=20.0
        )
        # Should not have window violation when None
        window_violations = [v for v in violations if v.type == "insufficient_window"]
        assert len(window_violations) == 0


class TestEvaluateRiskForSignal:
    """Test evaluate_risk_for_signal with policy violations."""
    
    def test_evaluate_risk_no_violations(self):
        """Test risk evaluation with no violations."""
        risk_metrics = {
            "profit_factor": 1.5,
            "total_return": 10.0,
            "max_drawdown": 20.0,
            "total_trades": 50
        }
        risk_validation = {
            "trade_count": 50,
            "window_days": 800,
            "is_reliable": True
        }
        
        result = evaluate_risk_for_signal(
            risk_metrics=risk_metrics,
            risk_validation=risk_validation,
            cache_validation=None,
            window_days=800
        )
        
        assert result["is_blocked"] is False
        assert len(result["violations"]) == 0
        assert result["block_reason"] is None
    
    def test_evaluate_risk_insufficient_trades(self):
        """Test risk evaluation with insufficient trades."""
        risk_metrics = {
            "profit_factor": 1.5,
            "total_return": 10.0,
            "max_drawdown": 20.0,
            "total_trades": 10
        }
        risk_validation = {
            "trade_count": 10,
            "window_days": 800,
            "is_reliable": False
        }
        
        result = evaluate_risk_for_signal(
            risk_metrics=risk_metrics,
            risk_validation=risk_validation,
            cache_validation=None,
            window_days=800
        )
        
        assert result["is_blocked"] is True
        assert len(result["violations"]) == 1
        assert result["violations"][0]["type"] == "insufficient_trades"
        assert "Insuficientes trades" in result["block_reason"]
    
    def test_evaluate_risk_insufficient_window(self):
        """Test risk evaluation with insufficient window."""
        risk_metrics = {
            "profit_factor": 1.5,
            "total_return": 10.0,
            "max_drawdown": 20.0,
            "total_trades": 50
        }
        risk_validation = {
            "trade_count": 50,
            "window_days": 100,
            "is_reliable": True
        }
        
        result = evaluate_risk_for_signal(
            risk_metrics=risk_metrics,
            risk_validation=risk_validation,
            cache_validation=None,
            window_days=100
        )
        
        assert result["is_blocked"] is True
        assert len(result["violations"]) == 1
        assert result["violations"][0]["type"] == "insufficient_window"
        assert "Ventana de datos insuficiente" in result["block_reason"]
    
    def test_evaluate_risk_low_profit_factor(self):
        """Test risk evaluation with low profit factor."""
        risk_metrics = {
            "profit_factor": 0.5,
            "total_return": 10.0,
            "max_drawdown": 20.0,
            "total_trades": 50
        }
        
        result = evaluate_risk_for_signal(
            risk_metrics=risk_metrics,
            risk_validation=None,
            cache_validation=None,
            window_days=800
        )
        
        assert result["is_blocked"] is True
        assert len(result["violations"]) == 1
        assert result["violations"][0]["type"] == "low_profit_factor"
    
    def test_evaluate_risk_profit_factor_null(self):
        """Test risk evaluation with null profit factor (infinity)."""
        risk_metrics = {
            "profit_factor": None,  # Represents infinity
            "total_return": 10.0,
            "max_drawdown": 20.0,
            "total_trades": 50
        }
        
        result = evaluate_risk_for_signal(
            risk_metrics=risk_metrics,
            risk_validation=None,
            cache_validation=None,
            window_days=800
        )
        
        # None profit factor should generate a violation (not available)
        assert result["is_blocked"] is True
        pf_violations = [v for v in result["violations"] if v["type"] == "low_profit_factor"]
        assert len(pf_violations) == 1
    
    def test_evaluate_risk_multiple_violations(self):
        """Test risk evaluation with multiple violations."""
        risk_metrics = {
            "profit_factor": 0.5,
            "total_return": -5.0,
            "max_drawdown": 60.0,
            "total_trades": 10
        }
        
        result = evaluate_risk_for_signal(
            risk_metrics=risk_metrics,
            risk_validation=None,
            cache_validation=None,
            window_days=100
        )
        
        assert result["is_blocked"] is True
        assert len(result["violations"]) == 5
        violation_types = {v["type"] for v in result["violations"]}
        assert violation_types == {
            "insufficient_trades",
            "insufficient_window",
            "low_profit_factor",
            "negative_return",
            "high_drawdown"
        }
        assert len(result["block_reasons"]) == 5
    
    def test_evaluate_risk_stale_cache(self):
        """Test risk evaluation with stale cache."""
        cache_validation = {
            "is_stale": True,
            "reason": "Data is stale: 25.0 hours old"
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
        # Should return early, no violations from metrics
        assert len(result["violations"]) == 0
    
    def test_evaluate_risk_inconsistent_cache(self):
        """Test risk evaluation with inconsistent cache."""
        cache_validation = {
            "is_inconsistent": True,
            "reason": "Hash mismatch"
        }
        
        result = evaluate_risk_for_signal(
            risk_metrics=None,
            risk_validation=None,
            cache_validation=cache_validation,
            window_days=None
        )
        
        assert result["is_blocked"] is True
        assert "Hash mismatch" in result["block_reason"]
    
    def test_evaluate_risk_no_metrics(self):
        """Test risk evaluation with no metrics."""
        result = evaluate_risk_for_signal(
            risk_metrics=None,
            risk_validation=None,
            cache_validation=None,
            window_days=None
        )
        
        assert result["is_blocked"] is True
        assert "No risk metrics available" in result["block_reason"]

