from dataclasses import dataclass
from typing import List, Dict
import pandas as pd
from ..configs import settings
from ..strategies.base_strategy import BaseStrategy

@dataclass
class DailyResult:
    day: int
    demand: int
    forecast: float
    order_qty: int
    stock_start: int
    stock_end: int
    spoiled: int
    shortage: int
    cost_holding: float
    cost_shortage: float
    cost_spoilage: float
    cost_purchase: float
    total_cost: float

class Simulator:
    def __init__(self, strategy: BaseStrategy, initial_stock: int = 50, config: Dict = None):
        self.strategy = strategy
        self.current_stock = initial_stock
        self.pending_orders = [] # List of tuples (arrival_day, qty)
        self.stock_batches = [] # List of (qty, age_days) for FIFO/Spoilage
        self.config = config or {}
        
        # Initialize stock batches with initial stock (age 0)
        if initial_stock > 0:
            self.stock_batches.append({'qty': initial_stock, 'age': 0})

    def _get_setting(self, key, default):
        return self.config.get(key, default)

    def run(self, demand_series: List[int], forecast_series: List[float]) -> pd.DataFrame:
        results = []
        
        # Resolve settings once
        LEAD_TIME = self._get_setting('LEAD_TIME', settings.LEAD_TIME)
        SHELF_LIFE = self._get_setting('SHELF_LIFE', settings.SHELF_LIFE)
        COST = self._get_setting('COST', settings.COST)
        HOLDING_COST = self._get_setting('HOLDING_COST', settings.HOLDING_COST)
        SHORTAGE_COST = self._get_setting('SHORTAGE_COST', settings.SHORTAGE_COST)
        
        for day, (demand, forecast) in enumerate(zip(demand_series, forecast_series)):
            # 1. Receive Orders
            arrived_qty = 0
            new_pending = []
            for arrival_day, qty in self.pending_orders:
                if arrival_day == day:
                    arrived_qty += qty
                else:
                    new_pending.append((arrival_day, qty))
            self.pending_orders = new_pending
            
            if arrived_qty > 0:
                self.stock_batches.append({'qty': arrived_qty, 'age': 0})
            
            # Total stock available for sale
            stock_start = sum(b['qty'] for b in self.stock_batches)
            
            # 2. Determine Order (Strategy)
            # Strategy sees stock_start (available now) and pending orders
            # Note: Strategies might still access global settings if not updated. 
            # ideally strategies should also receive config, but for now assuming they rely on passed args or global.
            pending_qty = sum(qty for _, qty in self.pending_orders)
            order_qty = self.strategy.calculate_order_qty(stock_start, forecast, pending_qty)
            
            if order_qty > 0:
                self.pending_orders.append((day + LEAD_TIME, order_qty))
                
            # 3. Fulfill Demand (FIFO)
            qty_sold = 0
            shortage = 0
            remaining_demand = demand
            
            temp_batches = []
            for batch in self.stock_batches:
                if remaining_demand > 0:
                    take = min(batch['qty'], remaining_demand)
                    batch['qty'] -= take
                    remaining_demand -= take
                    qty_sold += take
                
                if batch['qty'] > 0:
                    temp_batches.append(batch)
            
            self.stock_batches = temp_batches
            
            if remaining_demand > 0:
                shortage = remaining_demand
            
            # 4. Spoilage (End of Day)
            spoiled = 0
            surviving_batches = []
            for batch in self.stock_batches:
                batch['age'] += 1
                if batch['age'] > SHELF_LIFE:
                    spoiled += batch['qty']
                else:
                    surviving_batches.append(batch)
            self.stock_batches = surviving_batches
            
            stock_end = sum(b['qty'] for b in self.stock_batches)
            
            # 5. Calculate Costs
            cost_purchase = order_qty * COST # Paid when ordered (simplified)
            cost_holding = stock_end * HOLDING_COST
            cost_shortage = shortage * SHORTAGE_COST
            cost_spoilage = spoiled * COST # Lost cost of goods
            
            total_cost = cost_purchase + cost_holding + cost_shortage + cost_spoilage
            
            results.append(DailyResult(
                day=day,
                demand=demand,
                forecast=forecast,
                order_qty=order_qty,
                stock_start=stock_start,
                stock_end=stock_end,
                spoiled=spoiled,
                shortage=shortage,
                cost_holding=cost_holding,
                cost_shortage=cost_shortage,
                cost_spoilage=cost_spoilage,
                cost_purchase=cost_purchase,
                total_cost=total_cost
            ))
            
        return pd.DataFrame([vars(r) for r in results])
