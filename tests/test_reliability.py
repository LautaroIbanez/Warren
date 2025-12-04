"""Tests for reliability logic and threshold validation."""
import pytest
from datetime import datetime, timedelta

from app.core.backtest import BacktestEngine, Trade
from app.core.strategy import Signal
from app.config import settings


class TestReliabilityLogic:
    """Test is_reliable flag based on various thresholds."""
    
    def test_reliable_with_sufficient_trades(self, backtest_engine):
        """Test is_reliable=True when trades >= MIN_TRADES_FOR_RELIABILITY."""
        trades = self._create_trades_with_metrics(
            count=settings.MIN_TRADES_FOR_RELIABILITY,
            profit_factor=1.5,
            total_return=10.0,
            max_drawdown=20.0
        )
        equity_curve = self._create_equity_curve_with_return(10000.0, 11000.0, len(trades))
        
        metrics = backtest_engine._calculate_metrics(trades, equity_curve)
        
        assert metrics["is_reliable"] is True
        assert metrics["total_trades"] >= settings.MIN_TRADES_FOR_RELIABILITY
    
    def test_unreliable_with_insufficient_trades(self, backtest_engine):
        """Test is_reliable=False when trades < MIN_TRADES_FOR_RELIABILITY."""
        trades = self._create_trades_with_metrics(
            count=settings.MIN_TRADES_FOR_RELIABILITY - 1,
            profit_factor=2.0,
            total_return=20.0,
            max_drawdown=10.0
        )
        equity_curve = self._create_equity_curve_with_return(10000.0, 12000.0, len(trades))
        
        metrics = backtest_engine._calculate_metrics(trades, equity_curve)
        
        assert metrics["is_reliable"] is False
        assert "Only" in metrics["reason"] or "trades" in metrics["reason"]
    
    def test_unreliable_with_low_profit_factor(self, backtest_engine):
        """Test is_reliable=False when profit_factor < MIN_PROFIT_FACTOR."""
        trades = self._create_trades_with_metrics(
            count=settings.MIN_TRADES_FOR_RELIABILITY,
            profit_factor=settings.MIN_PROFIT_FACTOR - 0.1,  # Below threshold
            total_return=5.0,
            max_drawdown=15.0
        )
        equity_curve = self._create_equity_curve_with_return(10000.0, 10500.0, len(trades))
        
        metrics = backtest_engine._calculate_metrics(trades, equity_curve)
        
        assert metrics["is_reliable"] is False
        assert "Profit factor" in metrics["reason"] or "profit_factor" in metrics["reason"].lower()
    
    def test_unreliable_with_negative_return(self, backtest_engine):
        """Test is_reliable=False when total_return <= MIN_TOTAL_RETURN_PCT."""
        trades = self._create_trades_with_metrics(
            count=settings.MIN_TRADES_FOR_RELIABILITY,
            profit_factor=1.2,
            total_return=-5.0,  # Negative return
            max_drawdown=20.0
        )
        equity_curve = self._create_equity_curve_with_return(10000.0, 9500.0, len(trades))
        
        metrics = backtest_engine._calculate_metrics(trades, equity_curve)
        
        assert metrics["is_reliable"] is False
        assert "return" in metrics["reason"].lower()
    
    def test_unreliable_with_high_drawdown(self, backtest_engine):
        """Test is_reliable=False when max_drawdown > MAX_DRAWDOWN_PCT."""
        trades = self._create_trades_with_metrics(
            count=settings.MIN_TRADES_FOR_RELIABILITY,
            profit_factor=1.5,
            total_return=10.0,
            max_drawdown=settings.MAX_DRAWDOWN_PCT + 10.0  # Above threshold
        )
        # Create equity curve with high drawdown
        equity_curve = [
            {"timestamp": "2022-01-01", "equity": 10000.0},
            {"timestamp": "2022-01-02", "equity": 15000.0},  # Peak
            {"timestamp": "2022-01-03", "equity": 6000.0},    # Large drawdown
            {"timestamp": "2022-01-04", "equity": 11000.0},  # Recovery
        ]
        
        metrics = backtest_engine._calculate_metrics(trades, equity_curve)
        
        assert metrics["is_reliable"] is False
        assert "drawdown" in metrics["reason"].lower()
    
    def test_reliable_with_all_thresholds_met(self, backtest_engine):
        """Test is_reliable=True when all thresholds are met."""
        trades = self._create_trades_with_metrics(
            count=settings.MIN_TRADES_FOR_RELIABILITY + 10,
            profit_factor=settings.MIN_PROFIT_FACTOR + 0.5,
            total_return=settings.MIN_TOTAL_RETURN_PCT + 5.0,
            max_drawdown=settings.MAX_DRAWDOWN_PCT - 10.0
        )
        equity_curve = self._create_equity_curve_with_return(10000.0, 11000.0, len(trades))
        
        metrics = backtest_engine._calculate_metrics(trades, equity_curve)
        
        assert metrics["is_reliable"] is True
        assert metrics["reason"] is None
    
    def test_reason_includes_all_failing_thresholds(self, backtest_engine):
        """Test that reason includes all failing thresholds."""
        trades = self._create_trades_with_metrics(
            count=settings.MIN_TRADES_FOR_RELIABILITY - 5,  # Too few trades
            profit_factor=settings.MIN_PROFIT_FACTOR - 0.2,  # Too low PF
            total_return=-10.0,  # Negative return
            max_drawdown=settings.MAX_DRAWDOWN_PCT + 20.0  # Too high drawdown
        )
        equity_curve = [
            {"timestamp": "2022-01-01", "equity": 10000.0},
            {"timestamp": "2022-01-02", "equity": 15000.0},
            {"timestamp": "2022-01-03", "equity": 5000.0},  # Large drawdown
            {"timestamp": "2022-01-04", "equity": 9000.0},   # Negative return
        ]
        
        metrics = backtest_engine._calculate_metrics(trades, equity_curve)
        
        assert metrics["is_reliable"] is False
        reason = metrics["reason"]
        # Should mention multiple issues
        assert ";" in reason or len(reason.split()) > 10
    
    def _create_trades_with_metrics(self, count, profit_factor, total_return, max_drawdown):
        """Helper to create trades that result in specific metrics."""
        base_time = datetime(2022, 1, 1)
        trades = []
        
        # Create winning and losing trades to achieve target profit factor
        num_winners = int(count * 0.6)  # 60% win rate
        num_losers = count - num_winners
        
        # Calculate target P&L per trade to achieve profit factor
        # If PF = profit/loss, and we want PF = target_pf
        # Let's assume average loss = -100, then average profit = target_pf * 100
        avg_loss = -100.0
        avg_profit = profit_factor * abs(avg_loss) if profit_factor > 0 else 0
        
        for i in range(num_winners):
            entry_price = 40000.0 + i * 10
            position_value = 1000.0
            position_size = position_value / entry_price
            
            # Calculate exit price to achieve target profit
            target_pnl = avg_profit
            exit_price = entry_price + (target_pnl / position_size)
            
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
        
        for i in range(num_losers):
            entry_price = 40000.0 + i * 10
            position_value = 1000.0
            position_size = position_value / entry_price
            
            # Calculate exit price to achieve target loss
            target_pnl = avg_loss
            exit_price = entry_price + (target_pnl / position_size)
            
            trade = Trade(
                entry_time=base_time + timedelta(days=num_winners + i),
                exit_time=base_time + timedelta(days=num_winners + i + 1),
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
    
    def _create_equity_curve_with_return(self, initial, final, num_points):
        """Helper to create equity curve with specific return."""
        base_time = datetime(2022, 1, 1)
        curve = [{"timestamp": base_time.isoformat(), "equity": initial}]
        
        # Linear interpolation
        for i in range(1, num_points):
            equity = initial + (final - initial) * (i / (num_points - 1))
            curve.append({
                "timestamp": (base_time + timedelta(days=i)).isoformat(),
                "equity": equity
            })
        
        return curve

