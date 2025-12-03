"""BacktestEngine - Simula trades usando señales de StrategyEngine."""
from typing import Optional
from dataclasses import dataclass
from datetime import datetime
import pandas as pd
import numpy as np

from app.core.strategy import StrategyEngine, Signal, Recommendation


@dataclass
class Trade:
    """Representa un trade simulado."""
    entry_time: datetime
    exit_time: Optional[datetime]
    entry_price: float
    exit_price: Optional[float]
    stop_loss: float
    take_profit: float
    signal: Signal
    confidence: float
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    exit_reason: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convierte a diccionario para JSON."""
        # Convertir timestamps a strings ISO
        entry_time_str = None
        if self.entry_time:
            if hasattr(self.entry_time, 'isoformat'):
                entry_time_str = self.entry_time.isoformat()
            else:
                entry_time_str = str(self.entry_time)
        
        exit_time_str = None
        if self.exit_time:
            if hasattr(self.exit_time, 'isoformat'):
                exit_time_str = self.exit_time.isoformat()
            else:
                exit_time_str = str(self.exit_time)
        
        return {
            "entry_time": entry_time_str,
            "exit_time": exit_time_str,
            "entry_price": float(self.entry_price) if self.entry_price is not None else None,
            "exit_price": float(self.exit_price) if self.exit_price is not None else None,
            "stop_loss": float(self.stop_loss) if self.stop_loss is not None else None,
            "take_profit": float(self.take_profit) if self.take_profit is not None else None,
            "signal": self.signal.value,
            "confidence": float(self.confidence) if self.confidence is not None else None,
            "pnl": float(self.pnl) if self.pnl is not None else None,
            "pnl_pct": float(self.pnl_pct) if self.pnl_pct is not None else None,
            "exit_reason": self.exit_reason
        }


@dataclass
class BacktestResult:
    """Resultado de un backtest."""
    trades: list[Trade]
    equity_curve: list[dict]
    metrics: dict
    
    def to_dict(self) -> dict:
        """Convierte a diccionario para JSON."""
        # Asegurar que equity_curve tenga timestamps como strings
        equity_curve_clean = []
        for point in self.equity_curve:
            clean_point = {}
            for key, value in point.items():
                if key == 'timestamp':
                    # Convertir timestamp a string si es necesario
                    if hasattr(value, 'isoformat'):
                        clean_point[key] = value.isoformat()
                    elif hasattr(value, 'strftime'):
                        clean_point[key] = value.strftime('%Y-%m-%dT%H:%M:%S')
                    else:
                        clean_point[key] = str(value)
                else:
                    clean_point[key] = float(value) if isinstance(value, (int, float)) else value
            equity_curve_clean.append(clean_point)
        
        return {
            "trades": [t.to_dict() for t in self.trades],
            "equity_curve": equity_curve_clean,
            "metrics": self.metrics
        }


class BacktestEngine:
    """Motor de backtesting que simula trades usando StrategyEngine."""
    
    def __init__(self, strategy_engine: Optional[StrategyEngine] = None):
        self.strategy_engine = strategy_engine or StrategyEngine()
        self.initial_capital = 10000.0  # Capital inicial para simulación
    
    def run(
        self,
        symbol: str,
        interval: str,
        candles: pd.DataFrame
    ) -> BacktestResult:
        """
        Ejecuta backtest sobre un conjunto de velas.
        
        Args:
            symbol: Símbolo del par
            interval: Intervalo de tiempo
            candles: DataFrame con velas históricas
        
        Returns:
            BacktestResult con trades, equity curve y métricas
        """
        if candles.empty or len(candles) < 50:
            return self._empty_result("Insufficient candles for backtest")
        
        # Validar columnas
        required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        missing_cols = [col for col in required_cols if col not in candles.columns]
        if missing_cols:
            return self._empty_result(f"Missing columns: {', '.join(missing_cols)}")
        
        # Ordenar por timestamp
        candles = candles.sort_values('timestamp').reset_index(drop=True)
        
        # Simular trades
        trades = []
        equity = self.initial_capital
        # Convertir timestamp a string ISO
        first_timestamp = candles.iloc[0]['timestamp']
        if hasattr(first_timestamp, 'isoformat'):
            first_timestamp_str = first_timestamp.isoformat()
        else:
            first_timestamp_str = str(first_timestamp)
        equity_curve = [{"timestamp": first_timestamp_str, "equity": equity}]
        
        i = 50  # Empezar después de tener suficientes velas para indicadores
        current_trade: Optional[Trade] = None
        
        while i < len(candles):
            candle = candles.iloc[i]
            prev_candles = candles.iloc[:i+1]
            
            # Si no hay trade abierto, buscar señal
            if current_trade is None:
                recommendation = self.strategy_engine.generate_recommendation(
                    symbol=symbol,
                    interval=interval,
                    candles=prev_candles
                )
                
                # Solo abrir trade si señal es BUY o SELL (no HOLD)
                if recommendation.signal in [Signal.BUY, Signal.SELL]:
                    # Verificar que tenemos SL/TP válidos
                    if recommendation.stop_loss and recommendation.take_profit:
                        current_trade = Trade(
                            entry_time=pd.to_datetime(candle['timestamp']),
                            exit_time=None,
                            entry_price=recommendation.entry_price or float(candle['close']),
                            exit_price=None,
                            stop_loss=recommendation.stop_loss,
                            take_profit=recommendation.take_profit,
                            signal=recommendation.signal,
                            confidence=recommendation.confidence,
                            exit_reason=None
                        )
            
            # Si hay trade abierto, verificar SL/TP
            if current_trade is not None:
                exit_price, exit_reason = self._check_exit(
                    trade=current_trade,
                    candle=candle
                )
                
                if exit_price is not None:
                    # Cerrar trade
                    current_trade.exit_time = pd.to_datetime(candle['timestamp'])
                    current_trade.exit_price = exit_price
                    current_trade.exit_reason = exit_reason
                    
                    # Calcular P&L
                    if current_trade.signal == Signal.BUY:
                        pnl = exit_price - current_trade.entry_price
                    else:  # SELL
                        pnl = current_trade.entry_price - exit_price
                    
                    pnl_pct = (pnl / current_trade.entry_price) * 100
                    current_trade.pnl = round(pnl, 2)
                    current_trade.pnl_pct = round(pnl_pct, 2)
                    
                    # Actualizar equity
                    equity += pnl
                    trades.append(current_trade)
                    current_trade = None
            
            # Registrar equity curve (convertir timestamp a string)
            timestamp = candle['timestamp']
            if hasattr(timestamp, 'isoformat'):
                timestamp_str = timestamp.isoformat()
            else:
                timestamp_str = str(timestamp)
            equity_curve.append({
                "timestamp": timestamp_str,
                "equity": round(equity, 2)
            })
            
            i += 1
        
        # Cerrar trade abierto al final si existe
        if current_trade is not None:
            last_candle = candles.iloc[-1]
            current_trade.exit_time = pd.to_datetime(last_candle['timestamp'])
            current_trade.exit_price = float(last_candle['close'])
            current_trade.exit_reason = "End of data"
            
            if current_trade.signal == Signal.BUY:
                pnl = current_trade.exit_price - current_trade.entry_price
            else:
                pnl = current_trade.entry_price - current_trade.exit_price
            
            pnl_pct = (pnl / current_trade.entry_price) * 100
            current_trade.pnl = round(pnl, 2)
            current_trade.pnl_pct = round(pnl_pct, 2)
            trades.append(current_trade)
        
        # Calcular métricas
        metrics = self._calculate_metrics(trades, equity_curve)
        
        return BacktestResult(
            trades=trades,
            equity_curve=equity_curve,
            metrics=metrics
        )
    
    def _check_exit(
        self,
        trade: Trade,
        candle: pd.Series
    ) -> tuple[Optional[float], Optional[str]]:
        """
        Verifica si un trade debe cerrarse por SL o TP.
        
        Returns:
            (exit_price, exit_reason) o (None, None) si no hay salida
        """
        high = float(candle['high'])
        low = float(candle['low'])
        close = float(candle['close'])
        
        if trade.signal == Signal.BUY:
            # SL: precio tocó stop_loss (low <= stop_loss)
            if low <= trade.stop_loss:
                return trade.stop_loss, "Stop Loss"
            # TP: precio tocó take_profit (high >= take_profit)
            if high >= trade.take_profit:
                return trade.take_profit, "Take Profit"
        else:  # SELL
            # SL: precio tocó stop_loss (high >= stop_loss)
            if high >= trade.stop_loss:
                return trade.stop_loss, "Stop Loss"
            # TP: precio tocó take_profit (low <= take_profit)
            if low <= trade.take_profit:
                return trade.take_profit, "Take Profit"
        
        return None, None
    
    def _calculate_metrics(
        self,
        trades: list[Trade],
        equity_curve: list[dict]
    ) -> dict:
        """Calcula métricas de riesgo y performance."""
        if not trades:
            return {
                "total_trades": 0,
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "expectancy": 0.0,
                "cagr": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0,
                "total_return": 0.0,
                "is_reliable": False,
                "reason": "No trades generated"
            }
        
        # Trades ganadores y perdedores
        winning_trades = [t for t in trades if t.pnl and t.pnl > 0]
        losing_trades = [t for t in trades if t.pnl and t.pnl <= 0]
        
        total_trades = len(trades)
        win_count = len(winning_trades)
        win_rate = (win_count / total_trades) * 100 if total_trades > 0 else 0.0
        
        # Profit factor
        total_profit = sum(t.pnl for t in winning_trades) if winning_trades else 0.0
        total_loss = abs(sum(t.pnl for t in losing_trades)) if losing_trades else 0.0
        profit_factor = total_profit / total_loss if total_loss > 0 else 0.0
        
        # Expectancy
        avg_win = total_profit / win_count if win_count > 0 else 0.0
        avg_loss = abs(total_loss / len(losing_trades)) if losing_trades else 0.0
        expectancy = (win_rate / 100 * avg_win) - ((100 - win_rate) / 100 * avg_loss)
        
        # Equity curve metrics
        equity_values = [e['equity'] for e in equity_curve]
        if len(equity_values) < 2:
            return self._empty_metrics("Insufficient equity curve data")
        
        initial_equity = equity_values[0]
        final_equity = equity_values[-1]
        total_return = ((final_equity - initial_equity) / initial_equity) * 100
        
        # CAGR (simplificado - asumiendo período de backtest)
        # Necesitaríamos timestamps para calcularlo correctamente
        # Por ahora usamos total_return como aproximación
        cagr = total_return  # Simplificado
        
        # Sharpe Ratio (simplificado - necesitaría retornos diarios)
        returns = [t.pnl_pct for t in trades if t.pnl_pct is not None]
        if returns:
            mean_return = np.mean(returns)
            std_return = np.std(returns)
            sharpe_ratio = (mean_return / std_return) * np.sqrt(252) if std_return > 0 else 0.0
        else:
            sharpe_ratio = 0.0
        
        # Max Drawdown
        peak = initial_equity
        max_drawdown = 0.0
        for equity in equity_values:
            if equity > peak:
                peak = equity
            drawdown = ((peak - equity) / peak) * 100
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        # Reliability check
        is_reliable = total_trades >= 30  # Threshold mínimo
        
        return {
            "total_trades": total_trades,
            "win_rate": round(win_rate, 2),
            "profit_factor": round(profit_factor, 2),
            "expectancy": round(expectancy, 2),
            "cagr": round(cagr, 2),
            "sharpe_ratio": round(sharpe_ratio, 2),
            "max_drawdown": round(max_drawdown, 2),
            "total_return": round(total_return, 2),
            "is_reliable": is_reliable,
            "reason": None if is_reliable else f"Only {total_trades} trades (need 30+)"
        }
    
    def _empty_result(self, reason: str) -> BacktestResult:
        """Retorna resultado vacío con razón."""
        return BacktestResult(
            trades=[],
            equity_curve=[],
            metrics=self._empty_metrics(reason)
        )
    
    def _empty_metrics(self, reason: str) -> dict:
        """Retorna métricas vacías con razón."""
        return {
            "total_trades": 0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "expectancy": 0.0,
            "cagr": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "total_return": 0.0,
            "is_reliable": False,
            "reason": reason
        }

