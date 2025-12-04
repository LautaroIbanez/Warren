"""Tests for edge cases with deterministic fixtures."""
import pytest
from datetime import datetime, timedelta

from app.core.backtest import BacktestEngine
from app.config import settings


class TestEdgeCases:
    """Test edge cases with deterministic candle fixtures."""
    
    def test_no_trades_returns_zero_metrics(self, backtest_engine, deterministic_candles_small):
        """Test that no trades scenario returns zero metrics."""
        equity_curve = [{"timestamp": "2022-01-01", "equity": 10000.0}]
        
        metrics = backtest_engine._calculate_metrics([], equity_curve)
        
        assert metrics["total_trades"] == 0
        assert metrics["win_rate"] == 0.0
        assert metrics["profit_factor"] == 0.0
        assert metrics["expectancy"] == 0.0
        assert metrics["is_reliable"] is False
        assert "No trades" in metrics["reason"]
    
    def test_single_winning_trade(self, backtest_engine, single_winning_trade):
        """Test metrics with a single winning trade."""
        equity_curve = [
            {"timestamp": "2022-01-01", "equity": 10000.0},
            {"timestamp": "2022-01-02", "equity": 10000.0 + single_winning_trade.pnl}
        ]
        
        metrics = backtest_engine._calculate_metrics([single_winning_trade], equity_curve)
        
        assert metrics["total_trades"] == 1
        assert metrics["win_rate"] == 100.0  # 1 winner out of 1 trade
        assert metrics["profit_factor"] >= 999999.0  # No losses, so very high PF
        assert metrics["expectancy"] == pytest.approx(single_winning_trade.pnl, rel=0.01)
        assert metrics["is_reliable"] is False  # Only 1 trade, below threshold
    
    def test_single_losing_trade(self, backtest_engine, single_losing_trade):
        """Test metrics with a single losing trade."""
        equity_curve = [
            {"timestamp": "2022-01-01", "equity": 10000.0},
            {"timestamp": "2022-01-02", "equity": 10000.0 + single_losing_trade.pnl}
        ]
        
        metrics = backtest_engine._calculate_metrics([single_losing_trade], equity_curve)
        
        assert metrics["total_trades"] == 1
        assert metrics["win_rate"] == 0.0  # 0 winners out of 1 trade
        assert metrics["profit_factor"] == 0.0  # No profits, so PF = 0
        assert metrics["expectancy"] == pytest.approx(single_losing_trade.pnl, rel=0.01)
        assert metrics["is_reliable"] is False
    
    def test_only_breakeven_trades(self, backtest_engine, breakeven_trades):
        """Test metrics with only breakeven trades."""
        equity_curve = [
            {"timestamp": "2022-01-01", "equity": 10000.0},
            {"timestamp": "2022-01-02", "equity": 10000.0}  # No change
        ]
        
        metrics = backtest_engine._calculate_metrics(breakeven_trades, equity_curve)
        
        assert metrics["total_trades"] == len(breakeven_trades)
        assert metrics["win_rate"] == 0.0  # No winners (breakeven don't count)
        assert metrics["profit_factor"] == 0.0  # No profits
        # Expectancy should be negative due to fees
        assert metrics["expectancy"] < 0
        assert metrics["is_reliable"] is False
    
    def test_deterministic_candles_produce_consistent_results(self, backtest_engine, deterministic_candles_small):
        """Test that deterministic candles produce consistent backtest results."""
        # Run backtest twice with same candles
        result1 = backtest_engine.run("BTCUSDT", "1d", deterministic_candles_small)
        result2 = backtest_engine.run("BTCUSDT", "1d", deterministic_candles_small)
        
        # Results should be identical (within floating point precision)
        assert result1.metrics["total_trades"] == result2.metrics["total_trades"]
        assert result1.metrics["profit_factor"] == pytest.approx(result2.metrics["profit_factor"], rel=0.001)
        assert result1.metrics["win_rate"] == pytest.approx(result2.metrics["win_rate"], rel=0.001)
    
    def test_small_candle_series_handles_gracefully(self, backtest_engine, deterministic_candles_small):
        """Test that small candle series (20 candles) is handled gracefully."""
        # Should not crash, but may have limited trades
        result = backtest_engine.run("BTCUSDT", "1d", deterministic_candles_small)
        
        assert result.metrics is not None
        assert result.metrics["total_trades"] >= 0
        # With only 20 candles, we might have very few trades
        assert result.metrics["total_trades"] <= 10  # Reasonable upper bound
    
    def test_no_trend_candles(self, backtest_engine, deterministic_candles_no_trend):
        """Test backtest with sideways market (no clear trend)."""
        result = backtest_engine.run("BTCUSDT", "1d", deterministic_candles_no_trend)
        
        assert result.metrics is not None
        # Sideways market might have lower win rate or profit factor
        assert result.metrics["total_trades"] >= 0
    
    def test_downtrend_candles(self, backtest_engine, deterministic_candles_downtrend):
        """Test backtest with downward trending market."""
        result = backtest_engine.run("BTCUSDT", "1d", deterministic_candles_downtrend)
        
        assert result.metrics is not None
        # Downtrend might result in more losses
        assert result.metrics["total_trades"] >= 0

