/** E2E tests for Dashboard using Playwright. */
import { test, expect } from '@playwright/test';

test.describe('Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    // Mock API responses
    await page.route('**/recommendation/today', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          signal: 'HOLD',
          confidence: 0.0,
          entry_price: null,
          stop_loss: null,
          take_profit: null,
          rationale: 'Señal bloqueada',
          is_blocked: true,
          block_reason: 'Insuficientes trades: 25 < 30 mínimo requerido',
          block_reasons: ['Insuficientes trades: 25 < 30 mínimo requerido'],
          candles_hash: 'test_hash_123',
          as_of: '2022-01-01T12:00:00'
        })
      });
    });

    await page.route('**/risk/metrics', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          metrics: {
            total_trades: 25,
            win_rate: 55.0,
            profit_factor: 0.85,
            expectancy: -10.5,
            cagr: 5.2,
            sharpe_ratio: 0.8,
            max_drawdown: 15.5,
            total_return: 8.5,
            is_reliable: false
          },
          validation: {
            trade_count: 25,
            min_trades_required: 30,
            is_reliable: false
          },
          status: 'degraded',
          reason: 'Only 25 trades (need 30+)'
        })
      });
    });

    await page.goto('/');
  });

  test('displays blocked signal banner', async ({ page }) => {
    await expect(page.getByText('🚫 Señal Bloqueada')).toBeVisible();
    await expect(page.getByText(/Insuficientes trades/i)).toBeVisible();
  });

  test('blocked banner has red styling', async ({ page }) => {
    const banner = page.getByText('🚫 Señal Bloqueada').locator('..');
    await expect(banner).toHaveCSS('background-color', /rgb\(248, 215, 218\)|rgba\(248, 215, 218/);
  });

  test('displays minimum-trade warning in risk panel', async ({ page }) => {
    await expect(page.getByText(/Solo 25 trades/i)).toBeVisible();
    await expect(page.getByText(/se necesitan 30\+/i)).toBeVisible();
  });

  test('formats percentage metrics correctly', async ({ page }) => {
    await expect(page.getByText(/55\.00%/i)).toBeVisible(); // Win rate
    await expect(page.getByText(/5\.20%/i)).toBeVisible(); // CAGR
  });

  test('formats currency metrics correctly', async ({ page }) => {
    await expect(page.getByText(/\$-10\.50/i)).toBeVisible(); // Expectancy
  });
});

test.describe('Dashboard - Stale Signal', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('**/recommendation/today', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          signal: 'BUY',
          confidence: 0.8,
          entry_price: 40000.0,
          stop_loss: 38000.0,
          take_profit: 42000.0,
          rationale: 'Strong signal',
          is_stale_signal: true,
          stale_reason: 'Last candle is 25.5 hours old',
          candles_hash: 'test_hash_123',
          as_of: '2022-01-01T12:00:00'
        })
      });
    });

    await page.goto('/');
  });

  test('displays stale warning with yellow styling', async ({ page }) => {
    await expect(page.getByText('⚠️ Señal Antigua')).toBeVisible();
    const warning = page.getByText('⚠️ Señal Antigua').locator('..');
    await expect(warning).toHaveCSS('background-color', /rgb\(255, 243, 205\)|rgba\(255, 243, 205/);
  });
});

test.describe('Dashboard - Refresh', () => {
  test('refresh button updates data', async ({ page }) => {
    let refreshCallCount = 0;

    await page.route('**/refresh', async route => {
      refreshCallCount++;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          refresh: { success: true },
          snapshots: {
            recommendation: {
              signal: 'BUY',
              confidence: 0.85,
              candles_hash: 'new_hash_456',
              as_of: '2022-01-02T12:00:00'
            },
            candles: {
              candles: [],
              metadata: {
                candles_hash: 'new_hash_456',
                as_of: '2022-01-02T12:00:00'
              }
            },
            backtest: { trades: [], metrics: {} },
            risk: { metrics: {}, validation: {}, status: 'ok' }
          }
        })
      });
    });

    await page.goto('/');
    await page.getByRole('button', { name: /Refrescar Datos/i }).click();
    
    await expect(page.getByText(/Refrescando/i)).toBeVisible();
    await expect(page.getByText(/Refrescando/i)).not.toBeVisible({ timeout: 5000 });
    
    expect(refreshCallCount).toBeGreaterThan(0);
  });
});

