"""Integration tests for refresh endpoint."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
import pandas as pd
from datetime import datetime, timedelta
import json
import tempfile
import shutil
from pathlib import Path

from app.main import app
from app.config import settings


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def temp_data_dir():
    """Create temporary data directory."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


class TestRefreshEndpoint:
    """Integration tests for refresh endpoint."""
    
    @patch('app.api.refresh.IngestionWorker')
    @patch('app.api.refresh.get_today_recommendation')
    @patch('app.api.refresh.get_latest_backtest')
    @patch('app.api.refresh.get_candles')
    @patch('app.api.refresh.get_risk_metrics')
    def test_refresh_returns_snapshots(self, mock_risk, mock_candles, mock_backtest, mock_recommendation, mock_ingestion, client):
        """Test that refresh endpoint returns all snapshots."""
        # Mock ingestion worker
        mock_worker = Mock()
        mock_worker.refresh.return_value = {
            "success": True,
            "symbol": "BTCUSDT",
            "interval": "1d",
            "rows_added": 10
        }
        mock_ingestion.return_value = mock_worker
        
        # Mock snapshots
        mock_recommendation.return_value = {
            "signal": "BUY",
            "confidence": 0.8,
            "entry_price": 40000.0,
            "stop_loss": 38000.0,
            "take_profit": 42000.0,
            "rationale": "Test recommendation",
            "candles_hash": "test_hash_123",
            "as_of": "2022-01-01T00:00:00"
        }
        
        mock_backtest.return_value = {
            "trades": [{"entry_time": "2022-01-01", "pnl": 100.0}],
            "equity_curve": [{"timestamp": "2022-01-01", "equity": 10000.0}],
            "metrics": {
                "total_trades": 30,
                "profit_factor": 1.5,
                "total_return": 10.0
            }
        }
        
        mock_candles.return_value = {
            "candles": [{"timestamp": "2022-01-01", "close": 40000.0}],
            "metadata": {
                "candles_hash": "test_hash_123",
                "as_of": "2022-01-01T00:00:00"
            }
        }
        
        mock_risk.return_value = {
            "metrics": {
                "total_trades": 30,
                "profit_factor": 1.5,
                "is_reliable": True
            },
            "validation": {
                "trade_count": 30,
                "is_reliable": True
            },
            "status": "ok"
        }
        
        response = client.post("/refresh")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check refresh result
        assert "refresh" in data
        assert data["refresh"]["success"] is True
        
        # Check snapshots
        assert "snapshots" in data
        snapshots = data["snapshots"]
        assert "recommendation" in snapshots
        assert "backtest" in snapshots
        assert "candles" in snapshots
        assert "risk" in snapshots
    
    @patch('app.api.refresh.IngestionWorker')
    @patch('app.api.refresh.get_today_recommendation')
    @patch('app.api.refresh.get_latest_backtest')
    @patch('app.api.refresh.get_candles')
    @patch('app.api.refresh.get_risk_metrics')
    def test_refresh_snapshots_have_aligned_hashes(self, mock_risk, mock_candles, mock_backtest, mock_recommendation, mock_ingestion, client):
        """Test that snapshots have aligned hashes and timestamps."""
        # Mock ingestion worker
        mock_worker = Mock()
        mock_worker.refresh.return_value = {"success": True}
        mock_ingestion.return_value = mock_worker
        
        # Use consistent hash and timestamp across snapshots
        test_hash = "aligned_hash_12345"
        test_timestamp = "2022-01-01T12:00:00"
        
        mock_recommendation.return_value = {
            "signal": "BUY",
            "candles_hash": test_hash,
            "as_of": test_timestamp
        }
        
        mock_candles.return_value = {
            "candles": [],
            "metadata": {
                "candles_hash": test_hash,
                "as_of": test_timestamp
            }
        }
        
        mock_backtest.return_value = {"trades": [], "equity_curve": [], "metrics": {}}
        mock_risk.return_value = {"metrics": {}, "validation": {}, "status": "ok"}
        
        response = client.post("/refresh")
        
        assert response.status_code == 200
        data = response.json()
        
        snapshots = data["snapshots"]
        
        # Verify hash alignment
        assert snapshots["recommendation"]["candles_hash"] == test_hash
        assert snapshots["candles"]["metadata"]["candles_hash"] == test_hash
        
        # Verify timestamp alignment
        assert snapshots["recommendation"]["as_of"] == test_timestamp
        assert snapshots["candles"]["metadata"]["as_of"] == test_timestamp
    
    @patch('app.api.refresh.IngestionWorker')
    @patch('app.api.refresh.get_today_recommendation')
    @patch('app.api.refresh.get_latest_backtest')
    @patch('app.api.refresh.get_candles')
    @patch('app.api.refresh.get_risk_metrics')
    def test_refresh_handles_partial_failures(self, mock_risk, mock_candles, mock_backtest, mock_recommendation, mock_ingestion, client):
        """Test that refresh continues with partial snapshot failures."""
        # Mock ingestion worker
        mock_worker = Mock()
        mock_worker.refresh.return_value = {"success": True}
        mock_ingestion.return_value = mock_worker
        
        # Some snapshots succeed, some fail
        mock_recommendation.return_value = {"signal": "BUY"}
        mock_candles.side_effect = Exception("Candles error")
        mock_backtest.return_value = {"trades": []}
        mock_risk.side_effect = Exception("Risk error")
        
        response = client.post("/refresh")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have errors
        assert "errors" in data
        assert "candles" in data["errors"]
        assert "risk" in data["errors"]
        
        # Should still have successful snapshots
        assert "snapshots" in data
        assert data["snapshots"]["recommendation"] is not None
        assert data["snapshots"]["backtest"] is not None
    
    @patch('app.api.refresh.IngestionWorker')
    def test_refresh_fails_on_ingestion_error(self, mock_ingestion, client):
        """Test that refresh fails when ingestion fails."""
        mock_worker = Mock()
        mock_worker.refresh.return_value = {
            "success": False,
            "error": "Ingestion failed"
        }
        mock_ingestion.return_value = mock_worker
        
        response = client.post("/refresh")
        
        assert response.status_code == 503
        data = response.json()
        assert "refresh_failed" in data["detail"]["status"] or "error" in str(data).lower()
    
    @patch('app.api.refresh.IngestionWorker')
    @patch('app.api.refresh.get_today_recommendation')
    @patch('app.api.refresh.get_latest_backtest')
    @patch('app.api.refresh.get_candles')
    @patch('app.api.refresh.get_risk_metrics')
    def test_refresh_fails_when_all_snapshots_fail(self, mock_risk, mock_candles, mock_backtest, mock_recommendation, mock_ingestion, client):
        """Test that refresh fails when all snapshots fail."""
        mock_worker = Mock()
        mock_worker.refresh.return_value = {"success": True}
        mock_ingestion.return_value = mock_worker
        
        # All snapshots fail
        mock_recommendation.side_effect = Exception("Error 1")
        mock_candles.side_effect = Exception("Error 2")
        mock_backtest.side_effect = Exception("Error 3")
        mock_risk.side_effect = Exception("Error 4")
        
        response = client.post("/refresh")
        
        assert response.status_code == 503
        data = response.json()
        assert "snapshots_failed" in data["detail"]["status"] or "all" in str(data).lower()

