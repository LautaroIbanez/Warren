"""Tests for deterministic hashing."""
import pytest
import pandas as pd
from datetime import datetime

from app.data.candle_repository import CandleRepository
from app.data.backtest_repository import BacktestRepository
import tempfile
import shutil


class TestDeterministicHashing:
    """Test that hashing produces identical results across runs."""
    
    def test_candle_hash_is_deterministic(self, temp_data_dir):
        """Test that identical candle data produces identical hash."""
        repo = CandleRepository(data_dir=temp_data_dir)
        
        # Create deterministic candle data
        dates = pd.date_range(start='2022-01-01', periods=10, freq='D')
        candles1 = pd.DataFrame({
            'timestamp': dates,
            'open': [40000.0] * 10,
            'high': [41000.0] * 10,
            'low': [39000.0] * 10,
            'close': [40000.0] * 10,
            'volume': [1000000.0] * 10
        })
        
        # Save first time
        metadata1 = repo.save("BTCUSDT", "1d", candles1, merge_existing=False)
        hash1 = metadata1["source_file_hash"]
        
        # Save same data again (should produce same hash)
        candles2 = candles1.copy()
        metadata2 = repo.save("BTCUSDT", "1d", candles2, merge_existing=False)
        hash2 = metadata2["source_file_hash"]
        
        # Hashes should be identical
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 produces 64 hex characters
    
    def test_candle_hash_changes_with_data(self, temp_data_dir):
        """Test that different candle data produces different hash."""
        repo = CandleRepository(data_dir=temp_data_dir)
        
        dates = pd.date_range(start='2022-01-01', periods=10, freq='D')
        
        # First dataset
        candles1 = pd.DataFrame({
            'timestamp': dates,
            'open': [40000.0] * 10,
            'high': [41000.0] * 10,
            'low': [39000.0] * 10,
            'close': [40000.0] * 10,
            'volume': [1000000.0] * 10
        })
        
        # Second dataset (different close prices)
        candles2 = pd.DataFrame({
            'timestamp': dates,
            'open': [40000.0] * 10,
            'high': [41000.0] * 10,
            'low': [39000.0] * 10,
            'close': [41000.0] * 10,  # Different!
            'volume': [1000000.0] * 10
        })
        
        metadata1 = repo.save("BTCUSDT", "1d", candles1, merge_existing=False)
        metadata2 = repo.save("ETHUSDT", "1d", candles2, merge_existing=False)
        
        hash1 = metadata1["source_file_hash"]
        hash2 = metadata2["source_file_hash"]
        
        # Hashes should be different
        assert hash1 != hash2
    
    def test_candle_hash_same_across_loads(self, temp_data_dir):
        """Test that loading the same file produces the same hash."""
        repo = CandleRepository(data_dir=temp_data_dir)
        
        dates = pd.date_range(start='2022-01-01', periods=10, freq='D')
        candles = pd.DataFrame({
            'timestamp': dates,
            'open': [40000.0] * 10,
            'high': [41000.0] * 10,
            'low': [39000.0] * 10,
            'close': [40000.0] * 10,
            'volume': [1000000.0] * 10
        })
        
        # Save
        repo.save("BTCUSDT", "1d", candles, merge_existing=False)
        
        # Load multiple times
        _, metadata1 = repo.load("BTCUSDT", "1d")
        _, metadata2 = repo.load("BTCUSDT", "1d")
        
        hash1 = metadata1["source_file_hash"]
        hash2 = metadata2["source_file_hash"]
        
        # Hashes should be identical
        assert hash1 == hash2
    
    def test_backtest_hash_is_deterministic(self):
        """Test that backtest hash is deterministic."""
        repo = BacktestRepository()
        
        candles_hash = "test_candles_hash_12345"
        timestamp = "2022-01-01T12:00:00"
        
        # Calculate hash twice
        hash1 = repo._calculate_hash(candles_hash, timestamp)
        hash2 = repo._calculate_hash(candles_hash, timestamp)
        
        # Should be identical
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 produces 64 hex characters
    
    def test_backtest_hash_changes_with_input(self):
        """Test that different inputs produce different backtest hashes."""
        repo = BacktestRepository()
        
        hash1 = repo._calculate_hash("hash1", "2022-01-01T12:00:00")
        hash2 = repo._calculate_hash("hash2", "2022-01-01T12:00:00")
        hash3 = repo._calculate_hash("hash1", "2022-01-02T12:00:00")
        
        # All should be different
        assert hash1 != hash2
        assert hash1 != hash3
        assert hash2 != hash3

