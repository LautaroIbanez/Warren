"""Comprehensive tests for deterministic hashing."""
import pytest
import pandas as pd
from datetime import datetime
import hashlib

from app.data.candle_repository import CandleRepository
from app.data.backtest_repository import BacktestRepository


class TestHashDeterminism:
    """Test that hashing is deterministic for identical data."""
    
    def test_identical_candle_data_same_hash(self, temp_data_dir):
        """Test that identical candle data produces identical hash."""
        repo = CandleRepository(data_dir=temp_data_dir)
        
        # Create deterministic candle data
        dates = pd.date_range(start='2022-01-01', periods=100, freq='D')
        candles1 = pd.DataFrame({
            'timestamp': dates,
            'open': [40000.0] * 100,
            'high': [41000.0] * 100,
            'low': [39000.0] * 100,
            'close': [40000.0] * 100,
            'volume': [1000000.0] * 100
        })
        
        # Save first time
        metadata1 = repo.save("BTCUSDT", "1d", candles1, merge_existing=False)
        hash1 = metadata1["source_file_hash"]
        
        # Create identical data (different object, same content)
        candles2 = pd.DataFrame({
            'timestamp': dates,
            'open': [40000.0] * 100,
            'high': [41000.0] * 100,
            'low': [39000.0] * 100,
            'close': [40000.0] * 100,
            'volume': [1000000.0] * 100
        })
        
        # Save second time
        metadata2 = repo.save("BTCUSDT", "1d", candles2, merge_existing=False)
        hash2 = metadata2["source_file_hash"]
        
        # Hashes should be identical
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 produces 64 hex characters
    
    def test_hash_independent_of_order(self, temp_data_dir):
        """Test that hash is independent of DataFrame row order (after sorting)."""
        repo = CandleRepository(data_dir=temp_data_dir)
        
        dates = pd.date_range(start='2022-01-01', periods=10, freq='D')
        
        # Create candles in forward order
        candles1 = pd.DataFrame({
            'timestamp': dates,
            'open': [40000.0 + i * 100 for i in range(10)],
            'high': [41000.0 + i * 100 for i in range(10)],
            'low': [39000.0 + i * 100 for i in range(10)],
            'close': [40000.0 + i * 100 for i in range(10)],
            'volume': [1000000.0] * 10
        })
        
        # Create same candles in reverse order
        candles2 = candles1.iloc[::-1].copy()
        
        metadata1 = repo.save("BTCUSDT", "1d", candles1, merge_existing=False)
        metadata2 = repo.save("ETHUSDT", "1d", candles2, merge_existing=False)
        
        # Hashes should be identical (repository sorts by timestamp)
        assert metadata1["source_file_hash"] == metadata2["source_file_hash"]
    
    def test_hash_changes_with_data(self, temp_data_dir):
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
    
    def test_hash_changes_with_timestamp(self, temp_data_dir):
        """Test that different timestamps produce different hash."""
        repo = CandleRepository(data_dir=temp_data_dir)
        
        # First dataset
        dates1 = pd.date_range(start='2022-01-01', periods=10, freq='D')
        candles1 = pd.DataFrame({
            'timestamp': dates1,
            'open': [40000.0] * 10,
            'high': [41000.0] * 10,
            'low': [39000.0] * 10,
            'close': [40000.0] * 10,
            'volume': [1000000.0] * 10
        })
        
        # Second dataset (different timestamps)
        dates2 = pd.date_range(start='2022-01-02', periods=10, freq='D')
        candles2 = pd.DataFrame({
            'timestamp': dates2,
            'open': [40000.0] * 10,
            'high': [41000.0] * 10,
            'low': [39000.0] * 10,
            'close': [40000.0] * 10,
            'volume': [1000000.0] * 10
        })
        
        metadata1 = repo.save("BTCUSDT", "1d", candles1, merge_existing=False)
        metadata2 = repo.save("ETHUSDT", "1d", candles2, merge_existing=False)
        
        hash1 = metadata1["source_file_hash"]
        hash2 = metadata2["source_file_hash"]
        
        # Hashes should be different
        assert hash1 != hash2
    
    def test_backtest_hash_deterministic(self):
        """Test that backtest hash is deterministic for same inputs."""
        repo = BacktestRepository()
        
        candles_hash = "test_candles_hash_12345"
        timestamp = "2022-01-01T12:00:00"
        
        # Calculate hash multiple times
        hash1 = repo._calculate_hash(candles_hash, timestamp)
        hash2 = repo._calculate_hash(candles_hash, timestamp)
        hash3 = repo._calculate_hash(candles_hash, timestamp)
        
        # All should be identical
        assert hash1 == hash2 == hash3
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
    
    def test_hash_algorithm_consistency(self):
        """Test that hash algorithm produces consistent results."""
        # Test SHA256 directly
        content = "test_content_12345"
        hash1 = hashlib.sha256(content.encode('utf-8')).hexdigest()
        hash2 = hashlib.sha256(content.encode('utf-8')).hexdigest()
        
        assert hash1 == hash2
        assert len(hash1) == 64

