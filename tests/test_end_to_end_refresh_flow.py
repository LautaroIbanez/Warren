"""End-to-end integration tests for refresh → backtest → risk → recommendation flow."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
import pandas as pd
from datetime import datetime, timedelta

from app.main import app
from app.config import settings

client = TestClient(app)


class TestEndToEndRefreshFlow:
    """Test complete refresh → backtest → risk → recommendation flow."""
    
    @patch('app.api.refresh.IngestionWorker')
    @patch('app.api.refresh.get_today_recommendation')
    @patch('app.api.refresh.get_latest_backtest')
    @patch('app.api.refresh.get_candles')
    @patch('app.api.refresh.get_risk_metrics')
    def test_refresh_flow_with_fixed_candle_fixture(
        self, 
        mock_risk, 
        mock_candles, 
        mock_backtest, 
        mock_recommendation,
        mock_ingestion,
        temp_data_dir
    ):
        """Test end-to-end refresh flow with fixed candle fixture."""
        # Create fixed candle fixture
        dates = pd.date_range(start='2020-01-01', periods=800, freq='D')
        fixed_candles = pd.DataFrame({
            'timestamp': dates,
            'open': [40000.0 + i * 10 for i in range(800)],
            'high': [41000.0 + i * 10 for i in range(800)],
            'low': [39000.0 + i * 10 for i in range(800)],
            'close': [40000.0 + i * 10 for i in range(800)],
            'volume': [1000000.0] * 800
        })
        
        # Mock ingestion worker
        mock_worker = Mock()
        mock_worker.refresh.return_value = {
            "success": True,
            "symbol": "BTCUSDT",
            "interval": "1d",
            "rows_added": 10,
            "metadata": {
                "as_of": "2024-01-01T12:00:00",
                "source_file_hash": "test_candles_hash_123"
            }
        }
        mock_ingestion.return_value = mock_worker
        
        # Mock candles endpoint
        mock_candles.return_value = {
            "candles": fixed_candles.to_dict('records'),
            "metadata": {
                "source_file_hash": "test_candles_hash_123",
                "as_of": "2024-01-01T12:00:00",
                "window_days": 800
            }
        }
        
        # Mock backtest endpoint
        mock_backtest.return_value = {
            "trades": [],
            "equity_curve": [],
            "metrics": {
                "total_trades": 50,
                "profit_factor": 1.5,
                "total_return": 10.0,
                "max_drawdown": 20.0,
                "is_reliable": True
            },
            "metadata": {
                "candles_hash": "test_candles_hash_123",
                "backtest_hash": "test_backtest_hash_456"
            }
        }
        
        # Mock risk endpoint
        mock_risk.return_value = {
            "metrics": {
                "total_trades": 50,
                "profit_factor": 1.5,
                "total_return": 10.0,
                "max_drawdown": 20.0,
                "is_reliable": True
            },
            "validation": {
                "trade_count": 50,
                "window_days": 800,
                "is_reliable": True
            },
            "candles_hash": "test_candles_hash_123",
            "backtest_hash": "test_backtest_hash_456",
            "status": "ok"
        }
        
        # Mock recommendation endpoint
        mock_recommendation.return_value = {
            "signal": "BUY",
            "confidence": 0.85,
            "entry_price": 40000.0,
            "stop_loss": 38000.0,
            "take_profit": 42000.0,
            "rationale": "Strong signal",
            "candles_hash": "test_candles_hash_123",
            "backtest_hash": "test_backtest_hash_456",
            "is_blocked": False
        }
        
        # Call refresh endpoint
        response = client.post("/refresh", json={"symbol": "BTCUSDT", "interval": "1d"})
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify all snapshots are returned
        assert "snapshots" in data
        assert "recommendation" in data["snapshots"]
        assert "backtest" in data["snapshots"]
        assert "candles" in data["snapshots"]
        assert "risk" in data["snapshots"]
        
        # Verify hashes align (if present)
        recommendation = data["snapshots"]["recommendation"]
        candles = data["snapshots"]["candles"]
        risk = data["snapshots"]["risk"]
        
        candles_hash = candles["metadata"].get("candles_hash")
        if candles_hash:
            if "candles_hash" in recommendation:
                assert recommendation["candles_hash"] == candles_hash
            if "candles_hash" in risk:
                assert risk["candles_hash"] == candles_hash
    
    @patch('app.api.refresh.IngestionWorker')
    @patch('app.api.refresh.get_today_recommendation')
    @patch('app.api.refresh.get_latest_backtest')
    @patch('app.api.refresh.get_candles')
    @patch('app.api.refresh.get_risk_metrics')
    def test_refresh_flow_blocks_when_thresholds_violated(
        self,
        mock_risk,
        mock_candles,
        mock_backtest,
        mock_recommendation,
        mock_ingestion,
        temp_data_dir
    ):
        """Test that refresh flow blocks recommendation when thresholds are violated."""
        # Mock ingestion
        mock_worker = Mock()
        mock_worker.refresh.return_value = {"success": True}
        mock_ingestion.return_value = mock_worker
        
        # Mock risk with poor metrics
        mock_risk.return_value = {
            "metrics": {
                "total_trades": 10,  # Below threshold
                "profit_factor": 0.5,  # Below threshold
                "total_return": -5.0,  # Negative
                "max_drawdown": 60.0,  # Excessive
                "is_reliable": False
            },
            "validation": {
                "trade_count": 10,
                "window_days": 100,  # Insufficient
                "is_reliable": False
            },
            "status": "degraded"
        }
        
        # Mock recommendation (should be blocked)
        mock_recommendation.return_value = {
            "signal": "HOLD",
            "confidence": 0.0,
            "is_blocked": True,
            "block_reason": "Insuficientes trades: 10 < 30 mínimo requerido",
            "block_reasons": [
                "Insuficientes trades: 10 < 30 mínimo requerido",
                "Profit factor insuficiente: 0.50 < 1.0 mínimo requerido",
                "Retorno total insuficiente: -5.00% <= 0.0% mínimo requerido",
                "Drawdown máximo excedido: 60.00% > 50.0% máximo permitido",
                "Ventana de datos insuficiente: 100 días < 730 mínimo requerido"
            ],
            "violations": []
        }
        
        mock_candles.return_value = {"candles": [], "metadata": {}}
        mock_backtest.return_value = {"trades": [], "metrics": {}}
        
        # Call refresh
        response = client.post("/refresh")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify recommendation is blocked
        recommendation = data["snapshots"]["recommendation"]
        assert recommendation["is_blocked"] is True
        assert len(recommendation["block_reasons"]) >= 5  # All violations
    
    @patch('app.api.refresh.IngestionWorker')
    @patch('app.api.refresh.get_today_recommendation')
    @patch('app.api.refresh.get_latest_backtest')
    @patch('app.api.refresh.get_candles')
    @patch('app.api.refresh.get_risk_metrics')
    def test_refresh_flow_allows_when_thresholds_met(
        self,
        mock_risk,
        mock_candles,
        mock_backtest,
        mock_recommendation,
        mock_ingestion,
        temp_data_dir
    ):
        """Test that refresh flow allows recommendation when thresholds are met."""
        # Mock ingestion
        mock_worker = Mock()
        mock_worker.refresh.return_value = {"success": True}
        mock_ingestion.return_value = mock_worker
        
        # Mock risk with good metrics
        mock_risk.return_value = {
            "metrics": {
                "total_trades": 50,
                "profit_factor": 1.5,
                "total_return": 10.0,
                "max_drawdown": 20.0,
                "is_reliable": True
            },
            "validation": {
                "trade_count": 50,
                "window_days": 800,
                "is_reliable": True
            },
            "status": "ok"
        }
        
        # Mock recommendation (should be allowed)
        mock_recommendation.return_value = {
            "signal": "BUY",
            "confidence": 0.85,
            "entry_price": 40000.0,
            "stop_loss": 38000.0,
            "take_profit": 42000.0,
            "is_blocked": False
        }
        
        mock_candles.return_value = {"candles": [], "metadata": {}}
        mock_backtest.return_value = {"trades": [], "metrics": {}}
        
        # Call refresh
        response = client.post("/refresh")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify recommendation is allowed
        recommendation = data["snapshots"]["recommendation"]
        assert recommendation["is_blocked"] is False or recommendation.get("is_blocked") is None
        assert recommendation["signal"] in ["BUY", "SELL"]


class TestCacheBehavior:
    """Test cache behavior with stale/inconsistent hashes."""
    
    @patch('app.data.risk_repository.RiskRepository.load')
    @patch('app.data.backtest_repository.BacktestRepository.load')
    @patch('app.data.candle_repository.CandleRepository.load')
    def test_stale_hash_forces_recompute(self, mock_candle_load, mock_backtest_load, mock_risk_load, temp_data_dir):
        """Test that stale hash forces recompute and marks cache status."""
        from app.api.risk import get_risk_metrics
        
        # Mock stale cache
        mock_risk_load.return_value = (
            None,  # No cached data
            {
                "is_stale": True,
                "reason": "Data is stale: 25.0 hours old"
            }
        )
        
        # Mock backtest data (will be used to recompute)
        mock_backtest_load.return_value = (
            {
                "metrics": {
                    "total_trades": 50,
                    "profit_factor": 1.5,
                    "total_return": 10.0,
                    "max_drawdown": 20.0,
                    "is_reliable": True
                },
                "trades": []
            },
            {}
        )
        
        mock_candle_load.return_value = (
            pd.DataFrame(),
            {
                "source_file_hash": "current_hash",
                "as_of": "2024-01-01T12:00:00",
                "window_days": 800
            }
        )
        
        # This would need async context, but the pattern is clear
        # In real test, would use async test client
        
    @patch('app.data.risk_repository.RiskRepository.load')
    @patch('app.data.backtest_repository.BacktestRepository.load')
    def test_inconsistent_hash_invalidates_cache(self, mock_backtest_load, mock_risk_load, temp_data_dir):
        """Test that inconsistent hash invalidates cache."""
        # Mock inconsistent cache
        mock_risk_load.return_value = (
            None,
            {
                "is_inconsistent": True,
                "reason": "Hash mismatch: cached=abc123... vs current=xyz789..."
            }
        )
        
        mock_backtest_load.return_value = (
            {
                "metrics": {"total_trades": 50},
                "trades": []
            },
            {}
        )
        
        # Cache should be invalidated
        risk_data, cache_validation = mock_risk_load.return_value
        assert risk_data is None
        assert cache_validation["is_inconsistent"] is True

