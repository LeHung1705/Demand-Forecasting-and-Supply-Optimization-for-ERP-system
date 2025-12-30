import pandas as pd
import numpy as np
import sys
import os

# Ensure we can import modules
sys.path.append(os.getcwd())

from inventory_optimization_module.strategies.rule_based import RuleBasedStrategy
from inventory_optimization_module.strategies.math_based import MathBasedStrategy
from inventory_optimization_module.strategies.ai_ddmrp import AIDDMRPStrategy
from inventory_optimization_module.core.simulator import Simulator
from inventory_optimization_module.analysis.cost_calculator import calculate_summary

def load_forecast_data(filepath):
    """
    Loads forecast data from a CSV file.
    Expected format: date, qty
    """
    if not os.path.exists(filepath):
        print(f"Warning: Forecast file {filepath} not found.")
        return {}
    
    try:
        df = pd.read_csv(filepath)
        # Standardize column names if necessary
        df.columns = [c.lower() for c in df.columns]
        
        if 'date' not in df.columns or 'qty' not in df.columns:
            print("Error: CSV must contain 'date' and 'qty' columns.")
            return {}
            
        df['date'] = pd.to_datetime(df['date'])
        
        # Create a dictionary {timestamp: qty}
        return df.set_index('date')['qty'].to_dict()
    except Exception as e:
        print(f"Error loading forecast data: {e}")
        return {}

class MockForecaster:
    def __init__(self, data_path, store_id, product_id):
        print(f"Loading data from {data_path}...")
        # Assuming original_data.csv format based on earlier read
        # columns: store_id, product_id, dt, hours_sale...
        self.df = pd.read_csv(data_path)
        
        # Parse Dates
        self.df['dt'] = pd.to_datetime(self.df['dt'])
        
        # Filter Target
        self.df = self.df[(self.df['store_id'] == store_id) & (self.df['product_id'] == product_id)].copy()
        
        # Parse Sales
        # Data format example: "[1, 2, 3 ...]" (string) or similar
        def parse_sales(x):
            try:
                # Handle string list format
                if isinstance(x, str):
                    clean = x.strip('[]').replace('\n', '')
                    if ',' in clean:
                        items = clean.split(',')
                    else:
                        items = clean.split()
                    return sum(float(i) for i in items)
                return 0
            except:
                return 0
                
        self.df['daily_sales'] = self.df['hours_sale'].apply(parse_sales)
        self.df = self.df.sort_values('dt')
        
    def get_data(self, month=5):
        # Filter for Month
        mask = self.df['dt'].dt.month == month
        data_month = self.df[mask]
        
        if data_month.empty:
            print(f"Warning: No data found for Month {month}")
            return [], [], []
            
        demand_series = data_month['daily_sales'].astype(int).tolist()
        dates = data_month['dt'].tolist()
        
        # Mock Forecast (Baseline for non-AI strategies):
        # Actual Demand +/- Noise
        np.random.seed(42)
        noise = np.random.normal(0, 0.1, len(demand_series))
        forecast_series = [max(0, d * (1 + n)) for d, n in zip(demand_series, noise)]
        
        return demand_series, forecast_series, dates

def main():
    print("=== Inventory Optimization Demo ===")
    print("Target: Store 11, Product 267")
    print("Timeframe: Month 5 (May)")
    
    # 1. Setup Data
    data_path = 'data/original_data.csv' # or imputed_data.csv
    if not os.path.exists(data_path):
        # Fallback for the environment if file is missing
        print(f"Data file {data_path} not found. Using imputed_data.csv if available.")
        data_path = 'data/imputed_data.csv'
    
    forecaster = MockForecaster(data_path, store_id=11, product_id=267)
    demand, mock_forecast, dates = forecaster.get_data(month=5)
    
    if not demand:
        print("No data available to run simulation.")
        return

    print(f"\nSimulation Days: {len(demand)}")
    print(f"Total Demand: {sum(demand)}")
    
    # 2. Load Real Forecast Data
    forecast_file = 'data/forecast_output.csv'
    print(f"Loading real AI forecast from {forecast_file}...")
    real_forecast_dict = load_forecast_data(forecast_file)
    
    # Align real forecast with simulation dates
    # If date is missing in forecast, fallback to mock_forecast or 0.
    real_forecast_series = []
    missing_dates = 0
    for i, date in enumerate(dates):
        # Ensure we look up the Timestamp correctly
        # The dict keys are Timestamps, 'date' is Timestamp.
        if date in real_forecast_dict:
            real_forecast_series.append(real_forecast_dict[date])
        else:
            missing_dates += 1
            real_forecast_series.append(mock_forecast[i]) # Fallback
            
    if missing_dates > 0:
        print(f"Warning: {missing_dates} dates missing in real forecast CSV. Used mock fallback.")
    
    # 3. Define Strategies
    strategies = {
        "Rule-Based (Min 20/Max 50)": RuleBasedStrategy(min_stock=20, max_stock=50),
        "Math-Based (Newsvendor)": MathBasedStrategy(uncertainty_factor=0.2),
        "AI-DDMRP (Dynamic Buffers)": AIDDMRPStrategy(variability_factor=0.5)
    }
    
    # 4. Run Simulations
    results_summary = []
    
    for name, strategy in strategies.items():
        # Select the appropriate forecast input
        if "AI-DDMRP" in name:
            current_forecast = real_forecast_series
            print(f"\nRunning {name} with Real AI Forecast...")
        else:
            current_forecast = mock_forecast
            print(f"\nRunning {name} with Mock/Baseline Forecast...")

        sim = Simulator(strategy, initial_stock=30)
        df_res = sim.run(demand, current_forecast)
        
        summary = calculate_summary(df_res)
        summary['Strategy'] = name
        results_summary.append(summary)
        
        print(f"Total Cost: ${summary['Total Cost']:,.2f}")
        print(f"Shortage: {summary['Total Shortage']} units")
        print(f"Spoilage: {summary['Total Spoilage']} units")
        print(f"Fill Rate: {summary['Fill Rate']:.2%}")

    # 5. Compare
    df_compare = pd.DataFrame(results_summary)
    # Reorder columns for clarity
    cols = ['Strategy', 'Total Cost', 'Fill Rate', 'Total Shortage', 'Total Spoilage', 'Avg Stock']
    # Ensure columns exist before selecting
    cols = [c for c in cols if c in df_compare.columns]
    df_compare = df_compare[cols]
    
    print("\n=== FINAL COMPARISON ===")
    print(df_compare.to_string(index=False))

if __name__ == "__main__":
    main()