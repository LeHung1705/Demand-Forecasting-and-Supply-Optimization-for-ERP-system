import math
from .base_strategy import BaseStrategy
from ..configs import settings

class AIDDMRPStrategy(BaseStrategy):
    """
    AI-Driven Demand Driven MRP.
    Dynamically adjusts buffer zones based on AI Forecast.
    
    Buffer Zones:
    - Green Zone: Order Generation Point (Top of Green) to Order Up To (Top of Green + Green Qty)
    - Yellow Zone: Safety Cover (Consumed first)
    - Red Zone: Safety Stock (Emergency)
    
    Simplified for this demo:
    Target Stock = Forecast * (Lead Time + Review Period) * Factor + Safety Stock
    """
    def __init__(self, variability_factor=0.5):
        self.variability_factor = variability_factor

    def calculate_order_qty(self, current_stock: int, forecast: float, pending_orders: int = 0) -> int:
        # ADU (Average Daily Usage) is derived from the immediate AI forecast
        adu = forecast
        
        # Calculate Decoupled Lead Time (DLT)
        dlt = settings.LEAD_TIME
        
        # Calculate Buffers
        # Yellow Zone = ADU * DLT
        yellow_zone = adu * dlt
        
        # Red Zone = Yellow Zone * Lead Time Factor * Variability Factor
        # Simplified: Base safety stock relative to demand
        red_zone = yellow_zone * self.variability_factor
        
        # Green Zone = ADU * Order Cycle (1 day) (or Minimum Order Qty logic)
        green_zone = max(adu, 10) # Minimum imposed structure
        
        # Top of Yellow (Reorder Point)
        top_of_yellow = red_zone + yellow_zone
        
        # Top of Green (Order Up To Level)
        top_of_green = top_of_yellow + green_zone
        
        # Net Flow Position
        net_flow_position = current_stock + pending_orders
        
        # Logic: If Net Flow Position is below Top of Yellow, order up to Top of Green
        if net_flow_position < top_of_yellow:
            return int(math.ceil(top_of_green - net_flow_position))
        
        return 0
