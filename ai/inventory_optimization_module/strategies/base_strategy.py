from abc import ABC, abstractmethod

class BaseStrategy(ABC):
    @abstractmethod
    def calculate_order_qty(self, current_stock: int, forecast: float, pending_orders: int = 0) -> int:
        """
        Calculates the quantity to order for the next period.
        
        Args:
            current_stock (int): Current inventory level.
            forecast (float): Forecasted demand for the upcoming period(s).
            pending_orders (int): Stock currently on order but not yet received.
            
        Returns:
            int: The quantity to order.
        """
        pass
