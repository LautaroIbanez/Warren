/** Unit tests for Dashboard component. */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { Dashboard } from '../Dashboard';
import * as hooks from '../../hooks/useRecommendation';
import * as riskHooks from '../../hooks/useRiskMetrics';
import {
  mockBlockedRecommendation,
  mockStaleRecommendation,
  mockGoodRecommendation,
  mockRiskMetricsUnreliable
} from '../../test/mocks/api';

// Mock hooks
vi.mock('../../hooks/useRecommendation');
vi.mock('../../hooks/useCandles');
vi.mock('../../hooks/useBacktestTrades');
vi.mock('../../hooks/useRiskMetrics');
vi.mock('../../api/client');

describe('Dashboard', () => {
  it('displays blocked signal banner with red styling', async () => {
    vi.mocked(hooks.useRecommendation).mockReturnValue({
      data: mockBlockedRecommendation,
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
      const blockedBanner = screen.getByText(/🚫 Señal Bloqueada/i);
      expect(blockedBanner).toBeInTheDocument();
    });

    const blockReason = screen.getByText(/Insuficientes trades/i);
    expect(blockReason).toBeInTheDocument();
  });

  it('displays stale signal warning with yellow styling', async () => {
    vi.mocked(hooks.useRecommendation).mockReturnValue({
      data: mockStaleRecommendation,
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
      const staleWarning = screen.getByText(/⚠️ Señal Antigua/i);
      expect(staleWarning).toBeInTheDocument();
    });
  });

  it('displays reliability warning when risk data is unreliable', async () => {
    vi.mocked(hooks.useRecommendation).mockReturnValue({
      data: mockGoodRecommendation,
      loading: false,
      error: null,
      refetch: vi.fn(),
      updateData: vi.fn()
    } as any);

    vi.mocked(riskHooks.useRiskMetrics).mockReturnValue({
      data: mockRiskMetricsUnreliable,
      loading: false,
      error: null,
      refetch: vi.fn(),
      updateData: vi.fn()
    } as any);

    render(<Dashboard />);

    await waitFor(() => {
      const reliabilityWarning = screen.getByText(/Solo 25 trades/i);
      expect(reliabilityWarning).toBeInTheDocument();
      expect(reliabilityWarning).toHaveTextContent(/se necesitan 30\+/i);
    });
  });

  it('formats currency values correctly', async () => {
    vi.mocked(hooks.useRecommendation).mockReturnValue({
      data: mockGoodRecommendation,
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
      const entryPrice = screen.getByText(/\$40,000\.00/i);
      expect(entryPrice).toBeInTheDocument();
    });
  });

  it('formats percentage values correctly', async () => {
    vi.mocked(hooks.useRecommendation).mockReturnValue({
      data: { ...mockGoodRecommendation, confidence: 0.85 },
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
      const confidence = screen.getByText(/85\.0%/i);
      expect(confidence).toBeInTheDocument();
    });
  });
});

