from .base_strategy import BaseStrategy

class RuleBasedStrategy(BaseStrategy):
    """
    Min/Max (s, S) Policy.
    If Inventory Position < Min, Order up to Max.
    """
    def __init__(self, min_stock=20, max_stock=50):
        self.min_stock = min_stock
        self.max_stock = max_stock

    def calculate_order_qty(self, current_stock: int, forecast: float, pending_orders: int = 0) -> int:
        inventory_position = current_stock + pending_orders
        
        if inventory_position < self.min_stock:
            return max(0, self.max_stock - inventory_position)
        return 0
