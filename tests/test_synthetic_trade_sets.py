"""Unit tests for backtest metrics using synthetic trade sets."""
import pytest
from datetime import datetime, timedelta
import pandas as pd

from app.core.backtest import BacktestEngine, Trade
from app.core.strategy import Signal


class TestSyntheticTradeSets:
    """Test backtest metrics with synthetic trade sets (wins only, losses only, mixed)."""
    
    def test_metrics_with_wins_only(self, backtest_engine):
        """Test metrics calculation with only winning trades."""
        trades = self._create_winning_trades_set(count=50, avg_profit=100.0)
        equity_curve = self._create_equity_curve_from_trades(trades, initial_equity=10000.0)
        
        metrics = backtest_engine._calculate_metrics(trades, equity_curve)
        
        # Verify metrics
        assert metrics["total_trades"] == 50
        assert metrics["win_rate"] == 100.0  # All winners
        assert metrics["profit_factor"] is None  # Infinity (no losses)
        assert metrics["expectancy"] > 0  # Positive expectancy
        assert metrics["total_return"] > 0  # Positive return
        assert metrics["max_drawdown"] >= 0  # Non-negative
    
    def test_metrics_with_losses_only(self, backtest_engine):
        """Test metrics calculation with only losing trades."""
        trades = self._create_losing_trades_set(count=50, avg_loss=-100.0)
        equity_curve = self._create_equity_curve_from_trades(trades, initial_equity=10000.0)
        
        metrics = backtest_engine._calculate_metrics(trades, equity_curve)
        
        # Verify metrics
        assert metrics["total_trades"] == 50
        assert metrics["win_rate"] == 0.0  # No winners
        assert metrics["profit_factor"] == 0.0  # No profits
        assert metrics["expectancy"] < 0  # Negative expectancy
        assert metrics["total_return"] < 0  # Negative return
        assert metrics["max_drawdown"] > 0  # Has drawdown
    
    def test_metrics_with_mixed_trades(self, backtest_engine):
        """Test metrics calculation with mixed winning and losing trades."""
        trades = self._create_mixed_trades_set(
            winners=30, 
            losers=20, 
            avg_profit=150.0, 
            avg_loss=-100.0
        )
        equity_curve = self._create_equity_curve_from_trades(trades, initial_equity=10000.0)
        
        metrics = backtest_engine._calculate_metrics(trades, equity_curve)
        
        # Verify metrics
        assert metrics["total_trades"] == 50
        assert 0 < metrics["win_rate"] < 100  # Between 0 and 100
        assert metrics["profit_factor"] > 0  # Positive PF
        # Expected PF = (30 * 150) / (20 * 100) = 4500 / 2000 = 2.25
        assert metrics["profit_factor"] == pytest.approx(2.25, rel=0.1)
        assert metrics["expectancy"] > 0  # Positive expectancy (more winners)
        assert metrics["total_return"] > 0  # Positive return
    
    def test_profit_factor_calculation_wins_only(self, backtest_engine):
        """Test profit factor calculation with only wins (should be infinity/null)."""
        trades = self._create_winning_trades_set(count=10, avg_profit=100.0)
        equity_curve = self._create_equity_curve_from_trades(trades, initial_equity=10000.0)
        
        metrics = backtest_engine._calculate_metrics(trades, equity_curve)
        
        assert metrics["profit_factor"] is None  # Represents infinity
    
    def test_profit_factor_calculation_losses_only(self, backtest_engine):
        """Test profit factor calculation with only losses (should be 0)."""
        trades = self._create_losing_trades_set(count=10, avg_loss=-100.0)
        equity_curve = self._create_equity_curve_from_trades(trades, initial_equity=10000.0)
        
        metrics = backtest_engine._calculate_metrics(trades, equity_curve)
        
        assert metrics["profit_factor"] == 0.0
    
    def test_expectancy_calculation_mixed(self, backtest_engine):
        """Test expectancy calculation with mixed trades."""
        trades = self._create_mixed_trades_set(
            winners=20, 
            losers=10, 
            avg_profit=200.0, 
            avg_loss=-100.0
        )
        equity_curve = self._create_equity_curve_from_trades(trades, initial_equity=10000.0)
        
        metrics = backtest_engine._calculate_metrics(trades, equity_curve)
        
        # Expected expectancy = (20 * 200 + 10 * (-100)) / 30 = (4000 - 1000) / 30 = 100.0
        expected_expectancy = (20 * 200.0 + 10 * (-100.0)) / 30.0
        assert metrics["expectancy"] == pytest.approx(expected_expectancy, rel=0.1)
    
    def test_sharpe_ratio_with_volatile_equity(self, backtest_engine):
        """Test Sharpe ratio calculation with volatile equity curve."""
        trades = self._create_mixed_trades_set(
            winners=25, 
            losers=25, 
            avg_profit=120.0, 
            avg_loss=-100.0
        )
        # Create volatile equity curve
        equity_curve = self._create_volatile_equity_curve(initial=10000.0, final=11000.0, points=100)
        
        metrics = backtest_engine._calculate_metrics(trades, equity_curve)
        
        # Sharpe should be calculated if we have >=2 return points
        if metrics["sharpe_ratio"] is not None:
            assert isinstance(metrics["sharpe_ratio"], (int, float))
            assert metrics["sharpe_reason"] is None
        else:
            assert metrics["sharpe_reason"] is not None
    
    def test_cagr_with_multi_year_period(self, backtest_engine):
        """Test CAGR calculation with multi-year period."""
        trades = self._create_mixed_trades_set(
            winners=30, 
            losers=20, 
            avg_profit=150.0, 
            avg_loss=-100.0
        )
        # Create equity curve spanning 2 years
        base_date = datetime(2022, 1, 1)
        equity_curve = [
            {"timestamp": base_date.isoformat(), "equity": 10000.0},
            {"timestamp": (base_date + timedelta(days=730)).isoformat(), "equity": 12100.0}  # 21% over 2 years
        ]
        
        metrics = backtest_engine._calculate_metrics(trades, equity_curve)
        
        # CAGR should be annualized (approximately 10% per year for 21% over 2 years)
        assert metrics["cagr"] is not None
        assert metrics["cagr_label"] == "Annualized"
        assert metrics["cagr"] < metrics["total_return"]  # Annualized is less than total
    
    def test_max_drawdown_with_peak_and_trough(self, backtest_engine):
        """Test max drawdown calculation with clear peak and trough."""
        trades = self._create_mixed_trades_set(
            winners=20, 
            losers=10, 
            avg_profit=150.0, 
            avg_loss=-100.0
        )
        # Create equity curve with clear drawdown
        equity_curve = [
            {"timestamp": "2022-01-01", "equity": 10000.0},
            {"timestamp": "2022-01-02", "equity": 12000.0},  # Peak
            {"timestamp": "2022-01-03", "equity": 11000.0},
            {"timestamp": "2022-01-04", "equity": 8000.0},   # Trough (33.3% drawdown from peak)
            {"timestamp": "2022-01-05", "equity": 10000.0},  # Recovery
        ]
        
        metrics = backtest_engine._calculate_metrics(trades, equity_curve)
        
        # Max drawdown should be approximately 33.3% from peak (12000) to trough (8000)
        expected_dd = ((12000.0 - 8000.0) / 12000.0) * 100
        assert metrics["max_drawdown"] == pytest.approx(expected_dd, rel=0.1)
    
    def _create_winning_trades_set(self, count: int, avg_profit: float):
        """Create a set of only winning trades."""
        base_time = datetime(2022, 1, 1)
        trades = []
        
        for i in range(count):
            entry_price = 40000.0 + i * 10
            position_value = 1000.0
            position_size = position_value / entry_price
            
            # Calculate exit price to achieve target profit
            exit_price = entry_price + (avg_profit / position_size)
            
            trade = Trade(
                entry_time=base_time + timedelta(days=i),
                exit_time=base_time + timedelta(days=i + 1),
                entry_price=entry_price,
                exit_price=exit_price,
                stop_loss=entry_price * 0.95,
                take_profit=entry_price * 1.10,
                signal=Signal.BUY,
                confidence=0.7,
                position_size=position_size,
                position_value=position_value,
                entry_fee=position_value * 0.001,
                exit_fee=(position_size * exit_price) * 0.001,
                slippage_cost=position_value * 0.0005,
                exit_reason="Take Profit"
            )
            
            gross_pnl = (exit_price - entry_price) * position_size
            total_costs = trade.entry_fee + trade.exit_fee + trade.slippage_cost
            trade.pnl = gross_pnl - total_costs
            trade.pnl_pct = (trade.pnl / position_value) * 100
            
            trades.append(trade)
        
        return trades
    
    def _create_losing_trades_set(self, count: int, avg_loss: float):
        """Create a set of only losing trades."""
        base_time = datetime(2022, 1, 1)
        trades = []
        
        for i in range(count):
            entry_price = 40000.0 + i * 10
            position_value = 1000.0
            position_size = position_value / entry_price
            
            # Calculate exit price to achieve target loss
            exit_price = entry_price + (avg_loss / position_size)
            
            trade = Trade(
                entry_time=base_time + timedelta(days=i),
                exit_time=base_time + timedelta(days=i + 1),
                entry_price=entry_price,
                exit_price=exit_price,
                stop_loss=entry_price * 0.95,
                take_profit=entry_price * 1.10,
                signal=Signal.BUY,
                confidence=0.7,
                position_size=position_size,
                position_value=position_value,
                entry_fee=position_value * 0.001,
                exit_fee=(position_size * exit_price) * 0.001,
                slippage_cost=position_value * 0.0005,
                exit_reason="Stop Loss"
            )
            
            gross_pnl = (exit_price - entry_price) * position_size
            total_costs = trade.entry_fee + trade.exit_fee + trade.slippage_cost
            trade.pnl = gross_pnl - total_costs
            trade.pnl_pct = (trade.pnl / position_value) * 100
            
            trades.append(trade)
        
        return trades
    
    def _create_mixed_trades_set(self, winners: int, losers: int, avg_profit: float, avg_loss: float):
        """Create a mixed set of winning and losing trades."""
        winning_trades = self._create_winning_trades_set(winners, avg_profit)
        losing_trades = self._create_losing_trades_set(losers, avg_loss)
        
        # Interleave trades for more realistic sequence
        mixed = []
        max_count = max(len(winning_trades), len(losing_trades))
        for i in range(max_count):
            if i < len(winning_trades):
                mixed.append(winning_trades[i])
            if i < len(losing_trades):
                mixed.append(losing_trades[i])
        
        return mixed
    
    def _create_equity_curve_from_trades(self, trades, initial_equity: float):
        """Create equity curve from trade P&L."""
        base_time = datetime(2022, 1, 1)
        equity_curve = [{"timestamp": base_time.isoformat(), "equity": initial_equity}]
        
        current_equity = initial_equity
        for trade in trades:
            if trade.pnl is not None:
                current_equity += trade.pnl
            equity_curve.append({
                "timestamp": trade.exit_time.isoformat() if trade.exit_time else base_time.isoformat(),
                "equity": current_equity
            })
        
        return equity_curve
    
    def _create_volatile_equity_curve(self, initial: float, final: float, points: int):
        """Create a volatile equity curve."""
        import numpy as np
        np.random.seed(42)
        
        base_time = datetime(2022, 1, 1)
        equity_curve = [{"timestamp": base_time.isoformat(), "equity": initial}]
        
        current_equity = initial
        for i in range(1, points):
            # Random walk towards final value
            trend = (final - initial) / points
            noise = np.random.normal(0, abs(final - initial) * 0.1)
            current_equity = max(current_equity + trend + noise, initial * 0.5)
            equity_curve.append({
                "timestamp": (base_time + timedelta(days=i)).isoformat(),
                "equity": current_equity
            })
        
        return equity_curve

