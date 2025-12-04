/** DOM structure tests for Dashboard component. */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { Dashboard } from '../Dashboard';
import * as hooks from '../../hooks/useRecommendation';
import * as riskHooks from '../../hooks/useRiskMetrics';
import {
  mockBlockedRecommendation,
  mockGoodRecommendation
} from '../../test/mocks/api';

// Mock hooks
vi.mock('../../hooks/useRecommendation');
vi.mock('../../hooks/useCandles');
vi.mock('../../hooks/useBacktestTrades');
vi.mock('../../hooks/useRiskMetrics');
vi.mock('../../api/client');

describe('Dashboard DOM Structure', () => {
  it('renders blocked banner with correct structure', async () => {
    vi.mocked(hooks.useRecommendation).mockReturnValue({
      data: {
        ...mockBlockedRecommendation,
        candles_hash: 'abc123def456',
        backtest_hash: 'xyz789uvw012'
      },
      loading: false,
      error: null,
      refetch: vi.fn(),
      updateData: vi.fn()
    } as any);

    vi.mocked(riskHooks.useRiskMetrics).mockReturnValue({
      data: null,
      loading: false,
      error: null,
      refetch: vi.fn(),
      updateData: vi.fn()
    } as any);

    render(<Dashboard />);

    await waitFor(() => {
      // Check blocked banner exists
      const blockedBanner = screen.getByText(/🚫 Señal Bloqueada/i);
      expect(blockedBanner).toBeInTheDocument();
      
      // Check block reason exists
      const blockReason = screen.getByText(/Insuficientes trades/i);
      expect(blockReason).toBeInTheDocument();
      
      // Check hash display exists
      const hashDisplay = screen.getByText(/Hash de velas/i);
      expect(hashDisplay).toBeInTheDocument();
    });
  });

  it('renders allowed banner with correct structure', async () => {
    vi.mocked(hooks.useRecommendation).mockReturnValue({
      data: {
        ...mockGoodRecommendation,
        signal: 'BUY',
        entry_price: 40000.0,
        stop_loss: 38000.0,
        take_profit: 42000.0,
        candles_hash: 'abc123def456'
      },
      loading: false,
      error: null,
      refetch: vi.fn(),
      updateData: vi.fn()
    } as any);

    vi.mocked(riskHooks.useRiskMetrics).mockReturnValue({
      data: {
        metrics: {
          profit_factor: 1.5,
          win_rate: 60.0,
          total_return: 15.0,
          max_drawdown: 10.0,
          total_trades: 50
        },
        validation: {
          is_reliable: true,
          trade_count: 50,
          window_days: 800
        },
        status: 'ok'
      },
      loading: false,
      error: null,
      refetch: vi.fn(),
      updateData: vi.fn()
    } as any);

    render(<Dashboard />);

    await waitFor(() => {
      // Check allowed banner exists
      const allowedBanner = screen.getByText(/✅ Recomendación Activa/i);
      expect(allowedBanner).toBeInTheDocument();
      
      // Check signal direction
      const signal = screen.getByText(/BUY/i);
      expect(signal).toBeInTheDocument();
      
      // Check entry price
      const entryPrice = screen.getByText(/\$40,000/i);
      expect(entryPrice).toBeInTheDocument();
      
      // Check metrics summary
      const profitFactor = screen.getByText(/Profit Factor/i);
      expect(profitFactor).toBeInTheDocument();
    });
  });

  it('displays hash values correctly', async () => {
    vi.mocked(hooks.useRecommendation).mockReturnValue({
      data: {
        ...mockGoodRecommendation,
        candles_hash: 'abc123def4567890',
        backtest_hash: 'xyz789uvw0123456'
      },
      loading: false,
      error: null,
      refetch: vi.fn(),
      updateData: vi.fn()
    } as any);

    vi.mocked(riskHooks.useRiskMetrics).mockReturnValue({
      data: null,
      loading: false,
      error: null,
      refetch: vi.fn(),
      updateData: vi.fn()
    } as any);

    render(<Dashboard />);

    await waitFor(() => {
      // Check candles hash is displayed (truncated)
      const candlesHash = screen.getByText(/abc123def456/i);
      expect(candlesHash).toBeInTheDocument();
      
      // Check backtest hash is displayed (truncated)
      const backtestHash = screen.getByText(/xyz789uvw012/i);
      expect(backtestHash).toBeInTheDocument();
    });
  });

  it('displays violation list in blocked state', async () => {
    vi.mocked(hooks.useRecommendation).mockReturnValue({
      data: {
        ...mockBlockedRecommendation,
        block_reasons: [
          'Insuficientes trades: 25 < 30 mínimo requerido',
          'Profit factor insuficiente: 0.85 < 1.0 mínimo requerido',
          'Retorno total insuficiente: -5.00% <= 0.0% mínimo requerido'
        ]
      },
      loading: false,
      error: null,
      refetch: vi.fn(),
      updateData: vi.fn()
    } as any);

    vi.mocked(riskHooks.useRiskMetrics).mockReturnValue({
      data: null,
      loading: false,
      error: null,
      refetch: vi.fn(),
      updateData: vi.fn()
    } as any);

    render(<Dashboard />);

    await waitFor(() => {
      // Check all violation reasons are displayed
      const reason1 = screen.getByText(/Insuficientes trades/i);
      expect(reason1).toBeInTheDocument();
      
      const reason2 = screen.getByText(/Profit factor insuficiente/i);
      expect(reason2).toBeInTheDocument();
      
      const reason3 = screen.getByText(/Retorno total insuficiente/i);
      expect(reason3).toBeInTheDocument();
    });
  });
});

