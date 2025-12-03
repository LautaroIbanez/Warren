"""BacktestEngine - Simula trades usando señales de StrategyEngine."""
from typing import Optional
from dataclasses import dataclass
from datetime import datetime
import pandas as pd
import numpy as np

from app.core.strategy import StrategyEngine, Signal, Recommendation
from app.config import settings


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
    position_size: Optional[float] = None  # Tamaño de posición en unidades
    position_value: Optional[float] = None  # Valor de posición en capital
    entry_fee: Optional[float] = None  # Fee pagado al entrar
    exit_fee: Optional[float] = None  # Fee pagado al salir
    slippage_cost: Optional[float] = None  # Costo de slippage
    pnl: Optional[float] = None  # P&L nominal (después de fees)
    pnl_pct: Optional[float] = None  # P&L porcentual sobre capital
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
            "position_size": float(self.position_size) if self.position_size is not None else None,
            "position_value": float(self.position_value) if self.position_value is not None else None,
            "entry_fee": float(self.entry_fee) if self.entry_fee is not None else None,
            "exit_fee": float(self.exit_fee) if self.exit_fee is not None else None,
            "slippage_cost": float(self.slippage_cost) if self.slippage_cost is not None else None,
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
        self.initial_capital = settings.INITIAL_CAPITAL
        self.position_size_pct = settings.POSITION_SIZE_PCT / 100.0  # Convertir % a decimal
        self.trading_fee_pct = settings.TRADING_FEE_PCT / 100.0
        self.slippage_pct = settings.SLIPPAGE_PCT / 100.0
    
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
                        entry_price_base = recommendation.entry_price or float(candle['close'])
                        
                        # Aplicar slippage al precio de entrada
                        if recommendation.signal == Signal.BUY:
                            entry_price = entry_price_base * (1 + self.slippage_pct)  # Pagar más al comprar
                        else:  # SELL
                            entry_price = entry_price_base * (1 - self.slippage_pct)  # Recibir menos al vender
                        
                        # Calcular tamaño de posición basado en porcentaje del capital actual
                        position_value = equity * self.position_size_pct
                        position_size = position_value / entry_price  # Unidades
                        
                        # Calcular fees de entrada
                        entry_fee = position_value * self.trading_fee_pct
                        
                        current_trade = Trade(
                            entry_time=pd.to_datetime(candle['timestamp']),
                            exit_time=None,
                            entry_price=entry_price,
                            exit_price=None,
                            stop_loss=recommendation.stop_loss,
                            take_profit=recommendation.take_profit,
                            signal=recommendation.signal,
                            confidence=recommendation.confidence,
                            position_size=position_size,
                            position_value=position_value,
                            entry_fee=entry_fee,
                            exit_fee=None,
                            slippage_cost=position_value * self.slippage_pct,
                            exit_reason=None
                        )
            
            # Si hay trade abierto, verificar SL/TP
            if current_trade is not None:
                exit_price, exit_reason = self._check_exit(
                    trade=current_trade,
                    candle=candle
                )
                
                if exit_price is not None:
                    # Aplicar slippage al precio de salida
                    if current_trade.signal == Signal.BUY:
                        exit_price_with_slippage = exit_price * (1 - self.slippage_pct)  # Recibir menos al vender
                    else:  # SELL
                        exit_price_with_slippage = exit_price * (1 + self.slippage_pct)  # Pagar más al comprar
                    
                    # Cerrar trade
                    current_trade.exit_time = pd.to_datetime(candle['timestamp'])
                    current_trade.exit_price = exit_price_with_slippage
                    current_trade.exit_reason = exit_reason
                    
                    # Calcular valor de salida
                    exit_value = current_trade.position_size * exit_price_with_slippage
                    
                    # Calcular fees de salida
                    exit_fee = exit_value * self.trading_fee_pct
                    current_trade.exit_fee = exit_fee
                    
                    # Calcular P&L nominal (después de fees y slippage)
                    if current_trade.signal == Signal.BUY:
                        # Compramos a entry_price, vendemos a exit_price_with_slippage
                        gross_pnl = exit_value - current_trade.position_value
                    else:  # SELL (short)
                        # Vendemos a entry_price, compramos a exit_price_with_slippage
                        gross_pnl = current_trade.position_value - exit_value
                    
                    # P&L neto después de todos los costos
                    total_costs = current_trade.entry_fee + exit_fee + current_trade.slippage_cost
                    net_pnl = gross_pnl - total_costs
                    
                    # P&L porcentual sobre el capital usado (position_value)
                    pnl_pct = (net_pnl / current_trade.position_value) * 100 if current_trade.position_value > 0 else 0
                    
                    current_trade.pnl = round(net_pnl, 2)
                    current_trade.pnl_pct = round(pnl_pct, 2)
                    
                    # Actualizar equity con capital compuesto
                    equity += net_pnl
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
            exit_price_base = float(last_candle['close'])
            
            # Aplicar slippage al precio de salida
            if current_trade.signal == Signal.BUY:
                exit_price_with_slippage = exit_price_base * (1 - self.slippage_pct)
            else:  # SELL
                exit_price_with_slippage = exit_price_base * (1 + self.slippage_pct)
            
            current_trade.exit_time = pd.to_datetime(last_candle['timestamp'])
            current_trade.exit_price = exit_price_with_slippage
            current_trade.exit_reason = "End of data"
            
            # Calcular valor de salida
            exit_value = current_trade.position_size * exit_price_with_slippage
            
            # Calcular fees de salida
            exit_fee = exit_value * self.trading_fee_pct
            current_trade.exit_fee = exit_fee
            
            # Calcular P&L nominal (después de fees y slippage)
            if current_trade.signal == Signal.BUY:
                gross_pnl = exit_value - current_trade.position_value
            else:  # SELL (short)
                gross_pnl = current_trade.position_value - exit_value
            
            # P&L neto después de todos los costos
            total_costs = current_trade.entry_fee + exit_fee + current_trade.slippage_cost
            net_pnl = gross_pnl - total_costs
            
            # P&L porcentual sobre el capital usado
            pnl_pct = (net_pnl / current_trade.position_value) * 100 if current_trade.position_value > 0 else 0
            
            current_trade.pnl = round(net_pnl, 2)
            current_trade.pnl_pct = round(pnl_pct, 2)
            
            # Actualizar equity
            equity += net_pnl
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
        
        # Trades ganadores y perdedores (usar pnl_pct para métricas porcentuales)
        winning_trades = [t for t in trades if t.pnl_pct and t.pnl_pct > 0]
        losing_trades = [t for t in trades if t.pnl_pct and t.pnl_pct <= 0]
        
        total_trades = len(trades)
        win_count = len(winning_trades)
        win_rate = (win_count / total_trades) * 100 if total_trades > 0 else 0.0
        
        # Profit factor (usar P&L porcentual para reflejar retorno sobre capital)
        # Sumamos los pnl_pct ponderados por el valor de posición
        total_profit_pct_weighted = sum(
            t.pnl_pct * (t.position_value or 0) / 100.0 
            for t in winning_trades 
            if t.pnl_pct is not None and t.position_value
        ) if winning_trades else 0.0
        
        total_loss_pct_weighted = abs(sum(
            t.pnl_pct * (t.position_value or 0) / 100.0 
            for t in losing_trades 
            if t.pnl_pct is not None and t.position_value
        )) if losing_trades else 0.0
        
        # Alternativa: usar promedio de pnl_pct (más simple y refleja retorno por trade)
        avg_profit_pct = sum(t.pnl_pct for t in winning_trades) / len(winning_trades) if winning_trades else 0.0
        avg_loss_pct = abs(sum(t.pnl_pct for t in losing_trades) / len(losing_trades)) if losing_trades else 0.0
        profit_factor = avg_profit_pct / avg_loss_pct if avg_loss_pct > 0 else 0.0
        
        # Expectancy (P&L porcentual promedio por trade)
        total_pnl_pct = sum(t.pnl_pct for t in trades if t.pnl_pct is not None) if trades else 0.0
        expectancy_pct = total_pnl_pct / total_trades if total_trades > 0 else 0.0
        
        # Expectancy en valor nominal (para compatibilidad con UI)
        total_pnl = sum(t.pnl for t in trades if t.pnl is not None) if trades else 0.0
        expectancy = total_pnl / total_trades if total_trades > 0 else 0.0
        
        # Equity curve metrics con timestamps reales
        if len(equity_curve) < 2:
            return self._empty_metrics("Insufficient equity curve data")
        
        # Convertir equity_curve a DataFrame para cálculos temporales
        equity_df = pd.DataFrame(equity_curve)
        equity_df['timestamp'] = pd.to_datetime(equity_df['timestamp'])
        equity_df = equity_df.sort_values('timestamp').reset_index(drop=True)
        
        initial_equity = equity_df.iloc[0]['equity']
        final_equity = equity_df.iloc[-1]['equity']
        total_return = ((final_equity - initial_equity) / initial_equity) * 100
        
        # Calcular CAGR usando fechas reales
        start_date = equity_df.iloc[0]['timestamp']
        end_date = equity_df.iloc[-1]['timestamp']
        years = (end_date - start_date).days / 365.25
        
        if years > 0:
            # CAGR = ((Final Value / Initial Value) ^ (1 / Years)) - 1
            cagr = (((final_equity / initial_equity) ** (1 / years)) - 1) * 100
        else:
            cagr = total_return  # Si es menos de un año, usar total_return
        
        # Calcular Sharpe Ratio usando retornos diarios de equity_curve
        equity_df['returns'] = equity_df['equity'].pct_change()
        daily_returns = equity_df['returns'].dropna()
        
        if len(daily_returns) > 1:
            # Sharpe = (Mean Return - Risk Free Rate) / Std Dev * sqrt(252)
            # Asumimos risk-free rate = 0 para simplificar
            mean_daily_return = daily_returns.mean()
            std_daily_return = daily_returns.std()
            
            if std_daily_return > 0:
                # Annualizar: multiplicar por sqrt(252) para días de trading
                sharpe_ratio = (mean_daily_return / std_daily_return) * np.sqrt(252) * 100  # En porcentaje
            else:
                sharpe_ratio = 0.0
        else:
            sharpe_ratio = 0.0
        
        # Max Drawdown usando equity_curve
        equity_values = equity_df['equity'].values
        peak = initial_equity
        max_drawdown = 0.0
        for equity in equity_values:
            if equity > peak:
                peak = equity
            drawdown = ((peak - equity) / peak) * 100
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        # Validación de fiabilidad con umbrales
        from app.config import settings
        is_reliable = (
            total_trades >= settings.MIN_TRADES_FOR_RELIABILITY and
            profit_factor >= settings.MIN_PROFIT_FACTOR and
            total_return > settings.MIN_TOTAL_RETURN_PCT and
            max_drawdown <= settings.MAX_DRAWDOWN_PCT
        )
        
        # Razones de no confiabilidad
        reasons = []
        if total_trades < settings.MIN_TRADES_FOR_RELIABILITY:
            reasons.append(f"Only {total_trades} trades (need {settings.MIN_TRADES_FOR_RELIABILITY}+)")
        if profit_factor < settings.MIN_PROFIT_FACTOR:
            reasons.append(f"Profit factor {profit_factor:.2f} < {settings.MIN_PROFIT_FACTOR}")
        if total_return <= settings.MIN_TOTAL_RETURN_PCT:
            reasons.append(f"Total return {total_return:.2f}% <= {settings.MIN_TOTAL_RETURN_PCT}%")
        if max_drawdown > settings.MAX_DRAWDOWN_PCT:
            reasons.append(f"Max drawdown {max_drawdown:.2f}% > {settings.MAX_DRAWDOWN_PCT}%")
        
        return {
            "total_trades": total_trades,
            "win_rate": round(win_rate, 2),
            "profit_factor": round(profit_factor, 2),
            "expectancy": round(expectancy, 2),
            "cagr": round(cagr, 2),
            "sharpe_ratio": round(sharpe_ratio, 2),
            "max_drawdown": round(max_drawdown, 2),
            "total_return": round(total_return, 2),
            "period_years": round(years, 2),
            "is_reliable": is_reliable,
            "reason": None if is_reliable else "; ".join(reasons) if reasons else "Unknown"
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

