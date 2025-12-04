/** Tests for formatting utilities. */
import { describe, it, expect } from 'vitest';
import { formatPercent, formatCurrency, formatNumber } from '../formatting';

describe('formatting utilities', () => {
  describe('formatPercent', () => {
    it('formats positive percentages correctly', () => {
      expect(formatPercent(15.5)).toBe('15.50%');
      expect(formatPercent(0.123)).toBe('0.12%');
      expect(formatPercent(100)).toBe('100.00%');
    });

    it('formats negative percentages correctly', () => {
      expect(formatPercent(-5.5)).toBe('-5.50%');
      expect(formatPercent(-0.123)).toBe('-0.12%');
    });

    it('handles null and undefined', () => {
      expect(formatPercent(null)).toBe('N/A');
      expect(formatPercent(undefined)).toBe('N/A');
    });

    it('handles custom decimal places', () => {
      expect(formatPercent(15.555, 1)).toBe('15.6%');
      expect(formatPercent(15.555, 3)).toBe('15.555%');
    });

    it('handles zero', () => {
      expect(formatPercent(0)).toBe('0.00%');
    });
  });

  describe('formatCurrency', () => {
    it('formats positive currency correctly', () => {
      expect(formatCurrency(1000.5)).toBe('$1000.50');
      expect(formatCurrency(0.99)).toBe('$0.99');
      expect(formatCurrency(1000000)).toBe('$1000000.00');
    });

    it('formats negative currency correctly', () => {
      expect(formatCurrency(-100.5)).toBe('$-100.50');
      expect(formatCurrency(-0.99)).toBe('$-0.99');
    });

    it('handles null and undefined', () => {
      expect(formatCurrency(null)).toBe('N/A');
      expect(formatCurrency(undefined)).toBe('N/A');
    });

    it('handles custom decimal places', () => {
      expect(formatCurrency(1000.555, 1)).toBe('$1000.6');
      expect(formatCurrency(1000.555, 3)).toBe('$1000.555');
    });

    it('handles zero', () => {
      expect(formatCurrency(0)).toBe('$0.00');
    });
  });

  describe('formatNumber', () => {
    it('formats positive numbers correctly', () => {
      expect(formatNumber(15.5)).toBe('15.50');
      expect(formatNumber(0.123)).toBe('0.12');
      expect(formatNumber(100)).toBe('100.00');
    });

    it('formats negative numbers correctly', () => {
      expect(formatNumber(-5.5)).toBe('-5.50');
      expect(formatNumber(-0.123)).toBe('-0.12');
    });

    it('handles null and undefined', () => {
      expect(formatNumber(null)).toBe('N/A');
      expect(formatNumber(undefined)).toBe('N/A');
    });

    it('handles custom decimal places', () => {
      expect(formatNumber(15.555, 1)).toBe('15.6');
      expect(formatNumber(15.555, 3)).toBe('15.555');
    });

    it('handles zero', () => {
      expect(formatNumber(0)).toBe('0.00');
    });

    it('handles large numbers', () => {
      expect(formatNumber(999999.99)).toBe('999999.99');
      expect(formatNumber(1e6)).toBe('1000000.00');
    });
  });
});

