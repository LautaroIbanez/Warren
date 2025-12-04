"""Risk policy definitions and violation detection."""
from dataclasses import dataclass
from typing import Optional, List
from app.config import settings


@dataclass
class PolicyViolation:
    """Represents a single policy violation."""
    type: str  # 'insufficient_trades', 'low_profit_factor', 'negative_return', 'high_drawdown', 'insufficient_window'
    message: str
    actual_value: Optional[float] = None
    threshold_value: Optional[float] = None
    metric_name: Optional[str] = None


class RiskPolicy:
    """Centralized risk policy with threshold validation."""
    
    @staticmethod
    def check_trades(total_trades: int) -> Optional[PolicyViolation]:
        """Check if total trades meets minimum requirement."""
        if total_trades < settings.MIN_TRADES_FOR_RELIABILITY:
            return PolicyViolation(
                type="insufficient_trades",
                message=f"Insuficientes trades: {total_trades} < {settings.MIN_TRADES_FOR_RELIABILITY} mínimo requerido",
                actual_value=float(total_trades),
                threshold_value=float(settings.MIN_TRADES_FOR_RELIABILITY),
                metric_name="total_trades"
            )
        return None
    
    @staticmethod
    def check_window_days(window_days: int) -> Optional[PolicyViolation]:
        """Check if window days meets minimum requirement."""
        if window_days < settings.MIN_DATA_WINDOW_DAYS:
            return PolicyViolation(
                type="insufficient_window",
                message=f"Ventana de datos insuficiente: {window_days} días < {settings.MIN_DATA_WINDOW_DAYS} mínimo requerido",
                actual_value=float(window_days),
                threshold_value=float(settings.MIN_DATA_WINDOW_DAYS),
                metric_name="window_days"
            )
        return None
    
    @staticmethod
    def check_profit_factor(profit_factor: Optional[float]) -> Optional[PolicyViolation]:
        """Check if profit factor meets minimum requirement."""
        # Handle infinity/null cases
        if profit_factor is None:
            return PolicyViolation(
                type="low_profit_factor",
                message="Profit factor no disponible",
                actual_value=None,
                threshold_value=float(settings.MIN_PROFIT_FACTOR),
                metric_name="profit_factor"
            )
        
        # Check if it's infinity (represented as float('inf') or very large number)
        if profit_factor == float('inf') or (isinstance(profit_factor, float) and profit_factor > 1e10):
            return None  # Infinity is always acceptable
        
        if profit_factor < settings.MIN_PROFIT_FACTOR:
            return PolicyViolation(
                type="low_profit_factor",
                message=f"Profit factor insuficiente: {profit_factor:.2f} < {settings.MIN_PROFIT_FACTOR} mínimo requerido",
                actual_value=profit_factor,
                threshold_value=float(settings.MIN_PROFIT_FACTOR),
                metric_name="profit_factor"
            )
        return None
    
    @staticmethod
    def check_total_return(total_return: float) -> Optional[PolicyViolation]:
        """Check if total return meets minimum requirement."""
        if total_return <= settings.MIN_TOTAL_RETURN_PCT:
            return PolicyViolation(
                type="negative_return",
                message=f"Retorno total insuficiente: {total_return:.2f}% <= {settings.MIN_TOTAL_RETURN_PCT}% mínimo requerido",
                actual_value=total_return,
                threshold_value=float(settings.MIN_TOTAL_RETURN_PCT),
                metric_name="total_return"
            )
        return None
    
    @staticmethod
    def check_max_drawdown(max_drawdown: float) -> Optional[PolicyViolation]:
        """Check if max drawdown exceeds maximum allowed."""
        if max_drawdown > settings.MAX_DRAWDOWN_PCT:
            return PolicyViolation(
                type="high_drawdown",
                message=f"Drawdown máximo excedido: {max_drawdown:.2f}% > {settings.MAX_DRAWDOWN_PCT}% máximo permitido",
                actual_value=max_drawdown,
                threshold_value=float(settings.MAX_DRAWDOWN_PCT),
                metric_name="max_drawdown"
            )
        return None
    
    @staticmethod
    def evaluate_all(
        total_trades: int,
        window_days: Optional[int],
        profit_factor: Optional[float],
        total_return: float,
        max_drawdown: float
    ) -> List[PolicyViolation]:
        """Evaluate all policy checks and return list of violations."""
        violations = []
        
        # Check trades
        violation = RiskPolicy.check_trades(total_trades)
        if violation:
            violations.append(violation)
        
        # Check window days if provided
        if window_days is not None:
            violation = RiskPolicy.check_window_days(window_days)
            if violation:
                violations.append(violation)
        
        # Check profit factor
        violation = RiskPolicy.check_profit_factor(profit_factor)
        if violation:
            violations.append(violation)
        
        # Check total return
        violation = RiskPolicy.check_total_return(total_return)
        if violation:
            violations.append(violation)
        
        # Check max drawdown
        violation = RiskPolicy.check_max_drawdown(max_drawdown)
        if violation:
            violations.append(violation)
        
        return violations

