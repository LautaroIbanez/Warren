"""Snapshot/regression tests for refresh pipeline."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
import pandas as pd
from datetime import datetime
import json
import hashlib

from app.main import app
from app.config import settings


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestRefreshPipelineSnapshots:
    """Snapshot tests to ensure refresh pipeline consistency."""
    
    @patch('app.api.refresh.IngestionWorker')
    @patch('app.api.refresh.get_today_recommendation')
    @patch('app.api.refresh.get_latest_backtest')
    @patch('app.api.refresh.get_candles')
    @patch('app.api.refresh.get_risk_metrics')
    def test_refresh_snapshot_structure(self, mock_risk, mock_candles, mock_backtest, mock_recommendation, mock_ingestion, client):
        """Test that refresh returns consistent snapshot structure."""
        # Setup mocks
        mock_worker = Mock()
        mock_worker.refresh.return_value = {"success": True, "rows_added": 10}
        mock_ingestion.return_value = mock_worker
        
        test_hash = "snapshot_test_hash_123"
        test_timestamp = "2022-01-01T12:00:00"
        
        mock_recommendation.return_value = {
            "signal": "BUY",
            "confidence": 0.8,
            "candles_hash": test_hash,
            "as_of": test_timestamp
        }
        
        mock_backtest.return_value = {
            "trades": [],
            "equity_curve": [],
            "metrics": {"total_trades": 30}
        }
        
        mock_candles.return_value = {
            "candles": [],
            "metadata": {
                "candles_hash": test_hash,
                "as_of": test_timestamp
            }
        }
        
        mock_risk.return_value = {
            "metrics": {"total_trades": 30},
            "validation": {"is_reliable": True},
            "status": "ok"
        }
        
        response = client.post("/refresh")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify snapshot structure
        assert "refresh" in data
        assert "snapshots" in data
        
        snapshots = data["snapshots"]
        assert "recommendation" in snapshots
        assert "backtest" in snapshots
        assert "candles" in snapshots
        assert "risk" in snapshots
        
        # Verify hash alignment
        assert snapshots["recommendation"]["candles_hash"] == test_hash
        assert snapshots["candles"]["metadata"]["candles_hash"] == test_hash
    
    @patch('app.api.refresh.IngestionWorker')
    @patch('app.api.refresh.get_today_recommendation')
    @patch('app.api.refresh.get_latest_backtest')
    @patch('app.api.refresh.get_candles')
    @patch('app.api.refresh.get_risk_metrics')
    def test_refresh_metadata_consistency(self, mock_risk, mock_candles, mock_backtest, mock_recommendation, mock_ingestion, client):
        """Test that refresh updates metadata consistently."""
        mock_worker = Mock()
        mock_worker.refresh.return_value = {
            "success": True,
            "symbol": "BTCUSDT",
            "interval": "1d",
            "rows_added": 5
        }
        mock_ingestion.return_value = mock_worker
        
        # Consistent metadata across snapshots
        consistent_hash = hashlib.md5(b"test_data").hexdigest()
        consistent_timestamp = datetime.now().isoformat()
        
        mock_recommendation.return_value = {
            "signal": "BUY",
            "candles_hash": consistent_hash,
            "as_of": consistent_timestamp,
            "data_window": {"window_days": 100}
        }
        
        mock_candles.return_value = {
            "candles": [{"timestamp": "2022-01-01", "close": 40000.0}],
            "metadata": {
                "candles_hash": consistent_hash,
                "as_of": consistent_timestamp,
                "window_days": 100
            }
        }
        
        mock_backtest.return_value = {
            "trades": [],
            "equity_curve": [],
            "metrics": {}
        }
        
        mock_risk.return_value = {
            "metrics": {},
            "validation": {},
            "status": "ok"
        }
        
        response = client.post("/refresh")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify metadata consistency
        rec_hash = data["snapshots"]["recommendation"].get("candles_hash")
        candles_hash = data["snapshots"]["candles"]["metadata"].get("candles_hash")
        
        assert rec_hash == candles_hash == consistent_hash
        
        rec_timestamp = data["snapshots"]["recommendation"].get("as_of")
        candles_timestamp = data["snapshots"]["candles"]["metadata"].get("as_of")
        
        assert rec_timestamp == candles_timestamp == consistent_timestamp
    
    @patch('app.api.refresh.IngestionWorker')
    @patch('app.api.refresh.get_today_recommendation')
    @patch('app.api.refresh.get_latest_backtest')
    @patch('app.api.refresh.get_candles')
    @patch('app.api.refresh.get_risk_metrics')
    def test_refresh_recomputation_updates_cache(self, mock_risk, mock_candles, mock_backtest, mock_recommendation, mock_ingestion, client):
        """Test that refresh triggers recomputation and updates cache metadata."""
        mock_worker = Mock()
        mock_worker.refresh.return_value = {"success": True, "rows_added": 15}
        mock_ingestion.return_value = mock_worker
        
        new_hash = "new_hash_after_refresh"
        new_timestamp = "2022-01-02T12:00:00"
        
        # Simulate fresh data after refresh
        mock_recommendation.return_value = {
            "signal": "BUY",
            "candles_hash": new_hash,
            "as_of": new_timestamp
        }
        
        mock_candles.return_value = {
            "candles": [],
            "metadata": {
                "candles_hash": new_hash,
                "as_of": new_timestamp
            }
        }
        
        mock_backtest.return_value = {
            "trades": [],
            "equity_curve": [],
            "metrics": {"total_trades": 35}  # Updated count
        }
        
        mock_risk.return_value = {
            "metrics": {"total_trades": 35},
            "validation": {"is_reliable": True},
            "status": "ok",
            "cache_info": {
                "cached": False,
                "computed": True,
                "was_recomputed": True
            }
        }
        
        response = client.post("/refresh")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify recomputation occurred
        risk_data = data["snapshots"]["risk"]
        if "cache_info" in risk_data:
            assert risk_data["cache_info"].get("was_recomputed") is True or risk_data["cache_info"].get("computed") is True
        
        # Verify updated metrics
        assert data["snapshots"]["backtest"]["metrics"]["total_trades"] == 35
        assert data["snapshots"]["risk"]["metrics"]["total_trades"] == 35

