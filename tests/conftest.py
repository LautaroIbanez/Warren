"""Pytest configuration and shared fixtures."""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import shutil

from app.core.backtest import Trade, BacktestEngine
from app.core.strategy import Signal


@pytest.fixture
def temp_data_dir():
    """Create a temporary data directory for tests."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_candles():
    """Generate sample candle data for testing."""
    dates = pd.date_range(start='2022-01-01', periods=100, freq='D')
    np.random.seed(42)  # For reproducibility
    
    # Generate realistic price data
    base_price = 40000.0
    prices = []
    current_price = base_price
    
    for _ in dates:
        # Random walk with slight upward bias
        change = np.random.normal(0, 500)
        current_price = max(current_price + change, 1000)  # Don't go below $1000
        prices.append(current_price)
    
    candles = pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'high': [p * (1 + abs(np.random.normal(0, 0.02))) for p in prices],
        'low': [p * (1 - abs(np.random.normal(0, 0.02))) for p in prices],
        'close': prices,
        'volume': np.random.uniform(1000000, 10000000, len(dates))
    })
    
    # Ensure high >= close >= low
    candles['high'] = candles[['high', 'close']].max(axis=1)
    candles['low'] = candles[['low', 'close']].min(axis=1)
    
    return candles


@pytest.fixture
def deterministic_candles_small():
    """Small deterministic OHLCV series for edge case testing."""
    dates = pd.date_range(start='2022-01-01', periods=20, freq='D')
    
    # Deterministic price pattern: upward trend with some volatility
    base_price = 40000.0
    candles_data = []
    
    for i, date in enumerate(dates):
        # Simple pattern: price increases by $100 per day with small volatility
        close_price = base_price + (i * 100) + (50 if i % 3 == 0 else -30)
        open_price = close_price - 20
        high_price = close_price + 50
        low_price = close_price - 50
        volume = 1000000 + (i * 10000)
        
        candles_data.append({
            'timestamp': date,
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': volume
        })
    
    return pd.DataFrame(candles_data)


@pytest.fixture
def deterministic_candles_no_trend():
    """Deterministic candles with no clear trend (sideways market)."""
    dates = pd.date_range(start='2022-01-01', periods=15, freq='D')
    
    base_price = 40000.0
    candles_data = []
    
    for i, date in enumerate(dates):
        # Oscillate around base price
        close_price = base_price + (100 if i % 2 == 0 else -100)
        open_price = close_price - 10
        high_price = close_price + 30
        low_price = close_price - 30
        volume = 1000000
        
        candles_data.append({
            'timestamp': date,
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': volume
        })
    
    return pd.DataFrame(candles_data)


@pytest.fixture
def deterministic_candles_downtrend():
    """Deterministic candles with downward trend."""
    dates = pd.date_range(start='2022-01-01', periods=15, freq='D')
    
    base_price = 40000.0
    candles_data = []
    
    for i, date in enumerate(dates):
        # Price decreases by $200 per day
        close_price = base_price - (i * 200)
        open_price = close_price + 20
        high_price = close_price + 40
        low_price = close_price - 40
        volume = 1000000
        
        candles_data.append({
            'timestamp': date,
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': volume
        })
    
    return pd.DataFrame(candles_data)


@pytest.fixture
def winning_trades():
    """Create a list of winning trades."""
    base_time = datetime(2022, 1, 1)
    trades = []
    
    for i in range(10):
        entry_price = 40000.0 + i * 100
        exit_price = entry_price * 1.05  # 5% profit
        position_value = 1000.0
        position_size = position_value / entry_price
        
        trade = Trade(
            entry_time=base_time + timedelta(days=i*5),
            exit_time=base_time + timedelta(days=i*5 + 2),
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
        
        # Calculate P&L
        gross_pnl = (exit_price - entry_price) * position_size
        total_costs = trade.entry_fee + trade.exit_fee + trade.slippage_cost
        trade.pnl = gross_pnl - total_costs
        trade.pnl_pct = (trade.pnl / position_value) * 100
        
        trades.append(trade)
    
    return trades


@pytest.fixture
def losing_trades():
    """Create a list of losing trades."""
    base_time = datetime(2022, 1, 1)
    trades = []
    
    for i in range(5):
        entry_price = 40000.0 + i * 100
        exit_price = entry_price * 0.95  # 5% loss
        position_value = 1000.0
        position_size = position_value / entry_price
        
        trade = Trade(
            entry_time=base_time + timedelta(days=i*5),
            exit_time=base_time + timedelta(days=i*5 + 2),
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
        
        # Calculate P&L
        gross_pnl = (exit_price - entry_price) * position_size
        total_costs = trade.entry_fee + trade.exit_fee + trade.slippage_cost
        trade.pnl = gross_pnl - total_costs
        trade.pnl_pct = (trade.pnl / position_value) * 100
        
        trades.append(trade)
    
    return trades


@pytest.fixture
def breakeven_trades():
    """Create a list of breakeven trades (zero P&L)."""
    base_time = datetime(2022, 1, 1)
    trades = []
    
    for i in range(3):
        entry_price = 40000.0 + i * 100
        exit_price = entry_price  # No change
        position_value = 1000.0
        position_size = position_value / entry_price
        
        trade = Trade(
            entry_time=base_time + timedelta(days=i*5),
            exit_time=base_time + timedelta(days=i*5 + 2),
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
            exit_reason="Manual Exit"
        )
        
        # Calculate P&L (should be negative due to fees)
        gross_pnl = (exit_price - entry_price) * position_size
        total_costs = trade.entry_fee + trade.exit_fee + trade.slippage_cost
        trade.pnl = gross_pnl - total_costs
        trade.pnl_pct = (trade.pnl / position_value) * 100
        
        trades.append(trade)
    
    return trades


@pytest.fixture
def single_winning_trade():
    """Create a single winning trade."""
    base_time = datetime(2022, 1, 1)
    entry_price = 40000.0
    exit_price = 42000.0  # 5% profit
    position_value = 1000.0
    position_size = position_value / entry_price
    
    trade = Trade(
        entry_time=base_time,
        exit_time=base_time + timedelta(days=1),
        entry_price=entry_price,
        exit_price=exit_price,
        stop_loss=entry_price * 0.95,
        take_profit=entry_price * 1.10,
        signal=Signal.BUY,
        confidence=0.8,
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
    
    return trade


@pytest.fixture
def single_losing_trade():
    """Create a single losing trade."""
    base_time = datetime(2022, 1, 1)
    entry_price = 40000.0
    exit_price = 38000.0  # 5% loss
    position_value = 1000.0
    position_size = position_value / entry_price
    
    trade = Trade(
        entry_time=base_time,
        exit_time=base_time + timedelta(days=1),
        entry_price=entry_price,
        exit_price=exit_price,
        stop_loss=entry_price * 0.95,
        take_profit=entry_price * 1.10,
        signal=Signal.BUY,
        confidence=0.6,
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
    
    return trade


@pytest.fixture
def mixed_trades(winning_trades, losing_trades, breakeven_trades):
    """Combine winning, losing, and breakeven trades."""
    return winning_trades + losing_trades + breakeven_trades


@pytest.fixture
def equity_curve():
    """Generate a sample equity curve."""
    base_time = datetime(2022, 1, 1)
    initial_equity = 10000.0
    
    curve = [{"timestamp": base_time.isoformat(), "equity": initial_equity}]
    
    # Simulate equity growth with some volatility
    np.random.seed(42)
    current_equity = initial_equity
    
    for i in range(1, 50):
        # Random return between -2% and +3%
        return_pct = np.random.uniform(-0.02, 0.03)
        current_equity = current_equity * (1 + return_pct)
        curve.append({
            "timestamp": (base_time + timedelta(days=i)).isoformat(),
            "equity": round(current_equity, 2)
        })
    
    return curve


@pytest.fixture
def backtest_engine():
    """Create a BacktestEngine instance for testing."""
    return BacktestEngine()

