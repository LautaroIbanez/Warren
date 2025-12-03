"""StrategyEngine - Genera señales de trading basadas en indicadores."""
from enum import Enum
from typing import Optional
import pandas as pd
import numpy as np

from app.core.indicators import calculate_all_indicators


class Signal(str, Enum):
    """Señales de trading."""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class Recommendation:
    """Recomendación de trading con metadata."""
    
    def __init__(
        self,
        signal: Signal,
        confidence: float,
        entry_price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        rationale: str = ""
    ):
        self.signal = signal
        self.confidence = confidence  # 0.0 - 1.0
        self.entry_price = entry_price
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.rationale = rationale
    
    def to_dict(self) -> dict:
        """Convierte a diccionario para API."""
        return {
            "signal": self.signal.value,
            "confidence": round(self.confidence, 4),
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "rationale": self.rationale
        }


class StrategyEngine:
    """Motor de estrategia que genera recomendaciones diarias."""
    
    def __init__(self):
        self.min_candles_required = 50  # Mínimo para calcular indicadores
    
    def generate_recommendation(
        self,
        symbol: str,
        interval: str,
        candles: pd.DataFrame
    ) -> Recommendation:
        """
        Genera recomendación diaria basada en indicadores técnicos.
        
        Args:
            symbol: Símbolo del par (ej: BTCUSDT)
            interval: Intervalo de tiempo (ej: 1d)
            candles: DataFrame con columnas: timestamp, open, high, low, close, volume
        
        Returns:
            Recommendation con señal, confianza y rationale
        """
        if candles.empty or len(candles) < self.min_candles_required:
            return Recommendation(
                signal=Signal.HOLD,
                confidence=0.0,
                rationale=f"Insufficient data: {len(candles)} candles (need {self.min_candles_required})"
            )
        
        # Validar columnas requeridas
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        missing_cols = [col for col in required_cols if col not in candles.columns]
        if missing_cols:
            return Recommendation(
                signal=Signal.HOLD,
                confidence=0.0,
                rationale=f"Missing columns: {', '.join(missing_cols)}"
            )
        
        # Calcular indicadores
        try:
            df_with_indicators = calculate_all_indicators(candles)
        except Exception as e:
            return Recommendation(
                signal=Signal.HOLD,
                confidence=0.0,
                rationale=f"Error calculating indicators: {str(e)}"
            )
        
        # Obtener última vela (más reciente)
        latest = df_with_indicators.iloc[-1]
        prev = df_with_indicators.iloc[-2] if len(df_with_indicators) > 1 else latest
        
        # Verificar si hay valores NaN en indicadores críticos
        critical_indicators = ['rsi', 'macd', 'ema_12', 'ema_26', 'sma_20', 'atr']
        if any(pd.isna(latest.get(ind)) for ind in critical_indicators if ind in latest.index):
            return Recommendation(
                signal=Signal.HOLD,
                confidence=0.0,
                rationale="Insufficient data for indicator calculation (NaN values)"
            )
        
        # Estrategia: Momentum + Trend Alignment
        signal, confidence, rationale = self._momentum_trend_strategy(latest, prev)
        
        # Calcular niveles SL/TP basados en ATR
        entry_price = float(latest['close'])
        atr_value = float(latest['atr']) if not pd.isna(latest['atr']) else entry_price * 0.02
        
        stop_loss, take_profit = self._calculate_sl_tp(
            signal=signal,
            entry_price=entry_price,
            atr=atr_value
        )
        
        return Recommendation(
            signal=signal,
            confidence=confidence,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            rationale=rationale
        )
    
    def _momentum_trend_strategy(
        self,
        latest: pd.Series,
        prev: pd.Series
    ) -> tuple[Signal, float, str]:
        """
        Estrategia combinando momentum y alineación de tendencia.
        
        Señales BUY cuando:
        - EMA 12 > EMA 26 (tendencia alcista)
        - MACD > Signal y MACD > 0
        - RSI entre 40-70 (no sobrecomprado)
        - Precio > SMA 20
        
        Señales SELL cuando:
        - EMA 12 < EMA 26 (tendencia bajista)
        - MACD < Signal y MACD < 0
        - RSI entre 30-60 (no sobrevendido)
        - Precio < SMA 20
        """
        reasons = []
        buy_score = 0.0
        sell_score = 0.0
        
        # Trend alignment (EMA crossover)
        ema_12 = latest.get('ema_12', np.nan)
        ema_26 = latest.get('ema_26', np.nan)
        if not pd.isna(ema_12) and not pd.isna(ema_26):
            if ema_12 > ema_26:
                buy_score += 0.25
                reasons.append("EMA 12 > EMA 26 (uptrend)")
            else:
                sell_score += 0.25
                reasons.append("EMA 12 < EMA 26 (downtrend)")
        
        # MACD
        macd = latest.get('macd', np.nan)
        macd_signal = latest.get('macd_signal', np.nan)
        if not pd.isna(macd) and not pd.isna(macd_signal):
            if macd > macd_signal and macd > 0:
                buy_score += 0.25
                reasons.append("MACD bullish")
            elif macd < macd_signal and macd < 0:
                sell_score += 0.25
                reasons.append("MACD bearish")
        
        # RSI
        rsi = latest.get('rsi', np.nan)
        if not pd.isna(rsi):
            if 40 <= rsi <= 70:
                buy_score += 0.20
                reasons.append(f"RSI neutral-bullish ({rsi:.1f})")
            elif 30 <= rsi <= 60:
                sell_score += 0.20
                reasons.append(f"RSI neutral-bearish ({rsi:.1f})")
            elif rsi > 70:
                reasons.append(f"RSI overbought ({rsi:.1f})")
            elif rsi < 30:
                reasons.append(f"RSI oversold ({rsi:.1f})")
        
        # Price vs SMA
        close = latest.get('close', np.nan)
        sma_20 = latest.get('sma_20', np.nan)
        if not pd.isna(close) and not pd.isna(sma_20):
            if close > sma_20:
                buy_score += 0.15
                reasons.append("Price > SMA 20")
            else:
                sell_score += 0.15
                reasons.append("Price < SMA 20")
        
        # Momentum
        momentum = latest.get('momentum', np.nan)
        if not pd.isna(momentum):
            if momentum > 0:
                buy_score += 0.15
                reasons.append("Positive momentum")
            else:
                sell_score += 0.15
                reasons.append("Negative momentum")
        
        # Decidir señal
        confidence_threshold = 0.5
        
        if buy_score >= confidence_threshold and buy_score > sell_score:
            confidence = min(buy_score, 0.95)  # Cap at 95%
            return Signal.BUY, confidence, "; ".join(reasons)
        elif sell_score >= confidence_threshold and sell_score > buy_score:
            confidence = min(sell_score, 0.95)
            return Signal.SELL, confidence, "; ".join(reasons)
        else:
            # HOLD si no hay suficiente convicción
            max_score = max(buy_score, sell_score)
            confidence = max_score if max_score > 0 else 0.0
            rationale = "; ".join(reasons) if reasons else "No clear signal"
            return Signal.HOLD, confidence, rationale
    
    def _calculate_sl_tp(
        self,
        signal: Signal,
        entry_price: float,
        atr: float
    ) -> tuple[Optional[float], Optional[float]]:
        """
        Calcula Stop Loss y Take Profit basados en ATR.
        
        Para BUY:
        - SL: entry - (2 * ATR)
        - TP: entry + (3 * ATR)  # Risk:Reward 1:1.5
        
        Para SELL:
        - SL: entry + (2 * ATR)
        - TP: entry - (3 * ATR)
        """
        if signal == Signal.HOLD:
            return None, None
        
        atr_multiplier_sl = 2.0
        atr_multiplier_tp = 3.0
        
        if signal == Signal.BUY:
            stop_loss = entry_price - (atr_multiplier_sl * atr)
            take_profit = entry_price + (atr_multiplier_tp * atr)
        else:  # SELL
            stop_loss = entry_price + (atr_multiplier_sl * atr)
            take_profit = entry_price - (atr_multiplier_tp * atr)
        
        return round(stop_loss, 2), round(take_profit, 2)

