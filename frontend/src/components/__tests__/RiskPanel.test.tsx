/** Unit tests for RiskPanel component. */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { RiskPanel } from '../RiskPanel';
import { mockRiskMetricsUnreliable, mockRiskMetricsReliable } from '../../test/mocks/api';

describe('RiskPanel', () => {
  it('displays minimum-trade warning when unreliable', () => {
    render(<RiskPanel data={mockRiskMetricsUnreliable} loading={false} error={null} />);
    
    const warning = screen.getByText(/Solo 25 trades/i);
    expect(warning).toBeInTheDocument();
    expect(warning).toHaveTextContent(/se necesitan 30\+/i);
  });

  it('formats percentage metrics correctly', () => {
    render(<RiskPanel data={mockRiskMetricsReliable} loading={false} error={null} />);
    
    const winRate = screen.getByText(/60\.00%/i);
    expect(winRate).toBeInTheDocument();
    
    const cagr = screen.getByText(/12\.50%/i);
    expect(cagr).toBeInTheDocument();
  });

  it('formats currency metrics correctly', () => {
    render(<RiskPanel data={mockRiskMetricsReliable} loading={false} error={null} />);
    
    const expectancy = screen.getByText(/\$25\.50/i);
    expect(expectancy).toBeInTheDocument();
  });

  it('displays profit factor correctly', () => {
    render(<RiskPanel data={mockRiskMetricsReliable} loading={false} error={null} />);
    
    const profitFactor = screen.getByText(/1\.50/i);
    expect(profitFactor).toBeInTheDocument();
  });

  it('shows loading state', () => {
    render(<RiskPanel data={null} loading={true} error={null} />);
    
    expect(screen.getByText(/Cargando métricas/i)).toBeInTheDocument();
  });

  it('shows error state', () => {
    render(<RiskPanel data={null} loading={false} error="Test error" />);
    
    expect(screen.getByText(/Error: Test error/i)).toBeInTheDocument();
  });
});

