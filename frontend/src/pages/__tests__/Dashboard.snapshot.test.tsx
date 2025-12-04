/** Snapshot tests for Dashboard component rendering. */
import { describe, it, expect, vi } from 'vitest';
import { render } from '@testing-library/react';
import { Dashboard } from '../Dashboard';
import * as hooks from '../../hooks/useRecommendation';
import * as riskHooks from '../../hooks/useRiskMetrics';
import {
  mockBlockedRecommendation,
  mockGoodRecommendation,
  mockStaleRecommendation
} from '../../test/mocks/api';

// Mock hooks
vi.mock('../../hooks/useRecommendation');
vi.mock('../../hooks/useCandles');
vi.mock('../../hooks/useBacktestTrades');
vi.mock('../../hooks/useRiskMetrics');
vi.mock('../../api/client');

describe('Dashboard Snapshot Tests', () => {
  it('matches snapshot for blocked signal', () => {
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

    const { container } = render(<Dashboard />);
    expect(container).toMatchSnapshot();
  });

  it('matches snapshot for allowed signal', () => {
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

    const { container } = render(<Dashboard />);
    expect(container).toMatchSnapshot();
  });

  it('matches snapshot for stale signal', () => {
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

    const { container } = render(<Dashboard />);
    expect(container).toMatchSnapshot();
  });
});

