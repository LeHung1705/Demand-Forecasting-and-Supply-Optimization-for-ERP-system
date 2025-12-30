import numpy as np
from scipy.stats import norm
from .base_strategy import BaseStrategy
from ..configs import settings

class MathBasedStrategy(BaseStrategy):
    """
    Newsvendor Model.
    Optimizes order quantity based on critical ratio of costs.
    """
    def __init__(self, uncertainty_factor=0.2):
        self.uncertainty_factor = uncertainty_factor # Assumed std dev as % of forecast

        # Calculate Critical Ratio
        # Cost of Underestimating (Cu) = Profit Margin + Shortage Penalty
        # Profit Margin = Price - Cost
        self.cu = (settings.PRICE - settings.COST) + settings.SHORTAGE_COST
        
        # Cost of Overestimating (Co) = Cost + Holding Cost - Salvage (0)
        # Strictly speaking for perishable single-period (Newsvendor), Co is Cost - Salvage.
        # But in multi-period with holding, it's complex. We simplify for the Newsvendor approximation.
        self.co = settings.COST + settings.HOLDING_COST

        self.critical_ratio = self.cu / (self.cu + self.co)

    def calculate_order_qty(self, current_stock: int, forecast: float, pending_orders: int = 0) -> int:
        # We treat the "Order Up To" level as the optimal quantity for the period covering Lead Time + Review Period (1 day)
        # Demand during Lead Time + 1 Day
        review_period = 1
        relevant_horizon = settings.LEAD_TIME + review_period
        
        expected_demand = forecast * relevant_horizon
        std_dev = expected_demand * self.uncertainty_factor # Simplified uncertainty
        
        # Calculate optimal target stock level (Order-Up-To Level)
        # PPF (Percent Point Function) is the inverse of CDF
        target_stock = norm.ppf(self.critical_ratio, loc=expected_demand, scale=std_dev)
        target_stock = int(np.ceil(max(0, target_stock)))
        
        inventory_position = current_stock + pending_orders
        
        order_qty = max(0, target_stock - inventory_position)
        return order_qty
