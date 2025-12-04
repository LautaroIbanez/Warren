"""Unit tests for backtest metric calculations."""
import pytest
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from app.core.backtest import BacktestEngine, Trade
from app.core.strategy import Signal
from app.config import settings


class TestMetricCalculations:
    """Test metric calculation formulas."""
    
    def test_profit_factor_with_winning_and_losing_trades(self, backtest_engine, winning_trades, losing_trades):
        """Test profit factor calculation: sum(positive pnl) / abs(sum(negative pnl))."""
        trades = winning_trades + losing_trades
        equity_curve = self._create_simple_equity_curve(len(trades))
        
        metrics = backtest_engine._calculate_metrics(trades, equity_curve)
        
        # Calculate expected profit factor manually
        total_profit = sum(t.pnl for t in winning_trades if t.pnl is not None)
        total_loss = abs(sum(t.pnl for t in losing_trades if t.pnl is not None))
        expected_pf = total_profit / total_loss if total_loss > 0 else 0.0
        
        assert metrics["profit_factor"] == pytest.approx(expected_pf, rel=0.01)
        assert metrics["total_trades"] == len(trades)
    
    def test_profit_factor_with_only_wins(self, backtest_engine, winning_trades):
        """Test profit factor when there are no losses (should be null/infinity)."""
        equity_curve = self._create_simple_equity_curve(len(winning_trades))
        
        metrics = backtest_engine._calculate_metrics(winning_trades, equity_curve)
        
        # When no losses, profit factor should be null (represents infinity)
        assert metrics["profit_factor"] is None
    
    def test_profit_factor_with_only_losses(self, backtest_engine, losing_trades):
        """Test profit factor when there are no wins (should be 0)."""
        equity_curve = self._create_simple_equity_curve(len(losing_trades))
        
        metrics = backtest_engine._calculate_metrics(losing_trades, equity_curve)
        
        assert metrics["profit_factor"] == 0.0
    
    def test_win_rate_counts_only_winners(self, backtest_engine, mixed_trades):
        """Test win rate calculation - should only count winners, breakeven are neutral."""
        equity_curve = self._create_simple_equity_curve(len(mixed_trades))
        
        metrics = backtest_engine._calculate_metrics(mixed_trades, equity_curve)
        
        # Count winners manually
        winners = [t for t in mixed_trades if t.pnl is not None and t.pnl > 0]
        expected_win_rate = (len(winners) / len(mixed_trades)) * 100
        
        assert metrics["win_rate"] == pytest.approx(expected_win_rate, rel=0.01)
        assert metrics["total_trades"] == len(mixed_trades)
    
    def test_win_rate_with_breakeven_trades(self, backtest_engine, breakeven_trades):
        """Test win rate with only breakeven trades (should be 0%)."""
        equity_curve = self._create_simple_equity_curve(len(breakeven_trades))
        
        metrics = backtest_engine._calculate_metrics(breakeven_trades, equity_curve)
        
        assert metrics["win_rate"] == 0.0
        assert metrics["total_trades"] == len(breakeven_trades)
    
    def test_expectancy_includes_breakeven_as_zero(self, backtest_engine, mixed_trades):
        """Test expectancy calculation includes breakeven trades as zero P&L."""
        equity_curve = self._create_simple_equity_curve(len(mixed_trades))
        
        metrics = backtest_engine._calculate_metrics(mixed_trades, equity_curve)
        
        # Expectancy = average P&L per trade
        total_pnl = sum(t.pnl for t in mixed_trades if t.pnl is not None)
        expected_expectancy = total_pnl / len(mixed_trades)
        
        assert metrics["expectancy"] == pytest.approx(expected_expectancy, rel=0.01)
    
    def test_sharpe_ratio_no_arbitrary_scaling(self, backtest_engine, mixed_trades):
        """Test Sharpe ratio uses standard formula without ×100 scaling."""
        equity_curve = self._create_volatile_equity_curve(len(mixed_trades))
        
        metrics = backtest_engine._calculate_metrics(mixed_trades, equity_curve)
        
        # Sharpe should be reasonable (not multiplied by 100)
        # For typical trading, Sharpe is usually between -2 and 5
        assert metrics["sharpe_ratio"] is not None
        assert -10 < metrics["sharpe_ratio"] < 10
        # Should not be in percentage range (0-100)
        assert not (0 <= metrics["sharpe_ratio"] <= 100)
    
    def test_sharpe_ratio_insufficient_data(self, backtest_engine, mixed_trades):
        """Test Sharpe ratio returns None when <2 return points."""
        # Create equity curve with 2 points but same equity (no variation, only 1 return point after pct_change)
        equity_curve = [
            {"timestamp": "2022-01-01", "equity": 10000.0},
            {"timestamp": "2022-01-02", "equity": 10000.0},  # Same equity = 0% return, but we need >=2 returns
        ]
        
        # Actually need 3 points to get 2 return points after pct_change
        # With 2 points, pct_change gives 1 return, which is <2
        equity_curve = [
            {"timestamp": "2022-01-01", "equity": 10000.0},
            {"timestamp": "2022-01-02", "equity": 10000.0},
        ]
        
        metrics = backtest_engine._calculate_metrics(mixed_trades, equity_curve)
        
        assert metrics["sharpe_ratio"] is None
        assert metrics["sharpe_reason"] is not None
        assert "Insufficient return points" in metrics["sharpe_reason"] or "1 < 2" in metrics["sharpe_reason"]
    
    def test_sharpe_ratio_zero_volatility(self, backtest_engine, mixed_trades):
        """Test Sharpe ratio returns None when all returns are identical (zero volatility)."""
        # Create equity curve with constant equity (zero volatility)
        equity_curve = [
            {"timestamp": "2022-01-01", "equity": 10000.0},
            {"timestamp": "2022-01-02", "equity": 10000.0},
            {"timestamp": "2022-01-03", "equity": 10000.0},
        ]
        
        metrics = backtest_engine._calculate_metrics(mixed_trades, equity_curve)
        
        assert metrics["sharpe_ratio"] is None
        assert metrics["sharpe_reason"] is not None
        assert "Zero volatility" in metrics["sharpe_reason"]
    
    def test_cagr_sub_year_period(self, backtest_engine, mixed_trades):
        """Test CAGR returns total_return with label when period < 1 year."""
        # Create equity curve spanning less than 1 year
        base_time = datetime(2022, 1, 1)
        equity_curve = [
            {"timestamp": base_time.isoformat(), "equity": 10000.0},
            {"timestamp": (base_time + timedelta(days=180)).isoformat(), "equity": 11000.0},  # 6 months
        ]
        
        metrics = backtest_engine._calculate_metrics(mixed_trades, equity_curve)
        
        # CAGR should equal total_return (not annualized)
        expected_return = ((11000.0 - 10000.0) / 10000.0) * 100
        assert metrics["cagr"] == pytest.approx(expected_return, rel=0.01)
        assert metrics["cagr_label"] is not None
        assert "not annualized" in metrics["cagr_label"].lower() or "period < 1 year" in metrics["cagr_label"].lower()
    
    def test_cagr_multi_year_period(self, backtest_engine, mixed_trades):
        """Test CAGR is annualized when period >= 1 year."""
        # Create equity curve spanning 2 years
        base_time = datetime(2022, 1, 1)
        equity_curve = [
            {"timestamp": base_time.isoformat(), "equity": 10000.0},
            {"timestamp": (base_time + timedelta(days=730)).isoformat(), "equity": 12100.0},  # 2 years, 21% total
        ]
        
        metrics = backtest_engine._calculate_metrics(mixed_trades, equity_curve)
        
        # CAGR should be annualized (approximately 10% per year for 21% over 2 years)
        assert metrics["cagr"] is not None
        assert metrics["cagr_label"] == "Annualized"
        # CAGR should be less than total return (annualized)
        assert metrics["cagr"] < metrics["total_return"]
    
    def test_expectancy_has_currency_units(self, backtest_engine, mixed_trades):
        """Test expectancy includes currency units label."""
        equity_curve = self._create_simple_equity_curve(len(mixed_trades))
        
        metrics = backtest_engine._calculate_metrics(mixed_trades, equity_curve)
        
        assert "expectancy_units" in metrics
        assert metrics["expectancy_units"] == "USD"
        assert metrics["expectancy"] is not None
    
    def test_max_drawdown_calculation(self, backtest_engine, mixed_trades):
        """Test max drawdown calculation from equity curve."""
        # Create equity curve with a drawdown
        equity_curve = [
            {"timestamp": "2022-01-01", "equity": 10000.0},
            {"timestamp": "2022-01-02", "equity": 11000.0},  # Peak
            {"timestamp": "2022-01-03", "equity": 10500.0},
            {"timestamp": "2022-01-04", "equity": 9500.0},   # Drawdown from peak
            {"timestamp": "2022-01-05", "equity": 10000.0},
        ]
        
        metrics = backtest_engine._calculate_metrics(mixed_trades, equity_curve)
        
        # Max drawdown from peak (11000) to low (9500) = (11000-9500)/11000 * 100 = 13.64%
        expected_dd = ((11000.0 - 9500.0) / 11000.0) * 100
        assert metrics["max_drawdown"] == pytest.approx(expected_dd, rel=0.01)
    
    def test_total_return_calculation(self, backtest_engine, mixed_trades):
        """Test total return calculation from equity curve."""
        initial_equity = 10000.0
        final_equity = 12000.0
        
        equity_curve = [
            {"timestamp": "2022-01-01", "equity": initial_equity},
            {"timestamp": "2022-01-02", "equity": final_equity},
        ]
        
        metrics = backtest_engine._calculate_metrics(mixed_trades, equity_curve)
        
        expected_return = ((final_equity - initial_equity) / initial_equity) * 100
        assert metrics["total_return"] == pytest.approx(expected_return, rel=0.01)
    
    def test_empty_trades_returns_zero_metrics(self, backtest_engine):
        """Test that empty trade list returns zero metrics."""
        equity_curve = [{"timestamp": "2022-01-01", "equity": 10000.0}]
        
        metrics = backtest_engine._calculate_metrics([], equity_curve)
        
        assert metrics["total_trades"] == 0
        assert metrics["win_rate"] == 0.0
        assert metrics["profit_factor"] == 0.0
        assert metrics["expectancy"] == 0.0
        assert metrics["expectancy_units"] == "USD"
        assert metrics["cagr"] is None
        assert metrics["sharpe_ratio"] is None
        assert metrics["sharpe_reason"] is not None
        assert metrics["is_reliable"] is False
    
    def _create_simple_equity_curve(self, num_points):
        """Helper to create a simple equity curve."""
        base_time = datetime(2022, 1, 1)
        initial_equity = 10000.0
        
        curve = [{"timestamp": base_time.isoformat(), "equity": initial_equity}]
        
        for i in range(1, num_points):
            # Simple linear growth
            equity = initial_equity * (1 + 0.01 * i)
            curve.append({
                "timestamp": (base_time + timedelta(days=i)).isoformat(),
                "equity": equity
            })
        
        return curve
    
    def _create_volatile_equity_curve(self, num_points):
        """Helper to create a volatile equity curve for Sharpe calculation."""
        base_time = datetime(2022, 1, 1)
        initial_equity = 10000.0
        
        np.random.seed(42)
        curve = [{"timestamp": base_time.isoformat(), "equity": initial_equity}]
        
        current_equity = initial_equity
        for i in range(1, num_points):
            # Random walk
            change = np.random.normal(0, 100)
            current_equity = max(current_equity + change, 1000)
            curve.append({
                "timestamp": (base_time + timedelta(days=i)).isoformat(),
                "equity": current_equity
            })
        
        return curve

