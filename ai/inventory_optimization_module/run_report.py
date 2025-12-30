import argparse
import os
import sys
import pandas as pd
import numpy as np

# Add 'ai' folder to sys.path so we can treat inventory_optimization_module as a package
current_dir = os.path.dirname(os.path.abspath(__file__)) # inventory_optimization_module/
ai_dir = os.path.dirname(current_dir) # ai/
if ai_dir not in sys.path:
    sys.path.insert(0, ai_dir)

# Strictly use absolute imports
from inventory_optimization_module.strategies.rule_based import RuleBasedStrategy
from inventory_optimization_module.strategies.math_based import MathBasedStrategy
from inventory_optimization_module.strategies.ai_ddmrp import AIDDMRPStrategy
from inventory_optimization_module.core.simulator import Simulator
from inventory_optimization_module.analysis.cost_calculator import calculate_summary
from inventory_optimization_module.analysis.visualizer import Visualizer
from inventory_optimization_module.analysis.report_generator import ReportGenerator
from inventory_optimization_module.configs import settings

def load_forecast_data(filepath, store_id, product_id):
    """
    Loads forecast data. Preferred: optim_final_forecast.csv (Array format).
    """
    if not os.path.exists(filepath):
        print(f"Warning: Forecast file {filepath} not found.")
        return []
    
    try:
        df = pd.read_csv(filepath)
        
        # Check format 2: Store/Product filter (optim_final_forecast.csv)
        if 'daily_forecast' in df.columns:
            df = df[(df['store_id'] == int(store_id)) & (df['product_id'] == int(product_id))]
            if df.empty:
                return []
            
            row = df.iloc[0]
            val_str = row.get('daily_forecast', '')
            if isinstance(val_str, str):
                clean = val_str.replace('[', '').replace(']', '').replace('\n', ' ')
                parts = clean.split()
                return [float(p) for p in parts if p]

        # Check format 1: Date/Qty (Fallback)
        elif 'date' in df.columns and 'qty' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            # Return list for simplicity in this 7-day fixed logic
            return df['qty'].tolist()
                
        return []
    except Exception as e:
        print(f"Error loading forecast data: {e}")
        return []

def load_ground_truth(store_id, product_id, month):
    """
    Loads ground truth demand data for a specific store, product, and month.
    Matches main_demo.py logic.
    """
    # Try to find original_data.csv relative to this script
    base_dir = os.path.dirname(os.path.abspath(__file__)) # ai/inventory_optimization_module
    
    # Path candidates
    candidates = [
        os.path.join(base_dir, '../../backend/app/data/original_data.csv'), # From backend
        os.path.join(base_dir, '../data/original_data.csv'), # Local data
        'data/original_data.csv' # CWD
    ]
    
    data_path = None
    for p in candidates:
        if os.path.exists(p):
            data_path = p
            break
            
    if not data_path:
        print("Warning: original_data.csv not found. Cannot load ground truth.")
        return [], []

    try:
        print(f"Loading Ground Truth from {data_path}...")
        df = pd.read_csv(data_path)
        
        # Filter Target
        df = df[(df['store_id'] == int(store_id)) & (df['product_id'] == int(product_id))].copy()
        
        if df.empty:
            return [], []
            
        # Parse Dates
        df['dt'] = pd.to_datetime(df['dt'])
        
        # Filter for Month (May = 5)
        df = df[df['dt'].dt.month == month]
        df = df.sort_values('dt')
        
        if df.empty:
            print(f"No data found for Store {store_id}, Product {product_id} in Month {month}")
            return [], []

        # Parse Sales - MATCH main_demo.py LOGIC EXACTLY
        def parse_sales(x):
            try:
                if isinstance(x, str):
                    clean = x.strip('[]').replace('\n', '') # Removed space to match demo
                    if ',' in clean:
                        items = clean.split(',')
                    else:
                        items = clean.split()
                    return sum(float(i) for i in items)
                return 0
            except:
                return 0
                
        df['daily_sales'] = df['hours_sale'].apply(parse_sales)
        
        demand = df['daily_sales'].astype(int).tolist()
        dates_obj = df['dt'].tolist()
        dates_str = [d.strftime('%Y-%m-%d') for d in dates_obj]
        
        return demand, dates_str
        
    except Exception as e:
        print(f"Error loading ground truth: {e}")
        return [], []

def generate_recommendation_en(summary_df, sim_config):
    """
    Analyzes summary to generate English recommendation matching BPMN logic.
    """
    # Find strategy with Max Profit
    best_row = summary_df.loc[summary_df['Profit'].idxmax()]
    best_name = best_row['Strategy']
    max_profit = best_row['Profit']
    fill_rate = best_row['Fill Rate']
    
    # Calculate specific risks
    margin = sim_config["PRICE"] - sim_config["COST"]
    shortage_qty = best_row['Total Shortage']
    understock_risk = shortage_qty * margin
    overstock_risk = best_row['Holding Cost'] + best_row['Spoilage Cost']
    
    # "Actionable Insight"
    rec_text = (
        f"Recommended Strategy: {best_name}\n"
        f"- Projected Profit: ${max_profit:,.2f}\n"
        f"- Service Level (Fill Rate): {fill_rate:.1%} \n\n"
        f"ACTIONABLE INSIGHT:\n"
        f"Based on the multi-scenario simulation, this strategy offers the optimal trade-off:\n"
        f"1. Mitigates Understocking Risk (Opportunity Cost: ${understock_risk:,.2f})\n"
        f"2. Controls Overstocking Risk (Holding/Waste Cost: ${overstock_risk:,.2f})\n"
        f"Recommendation: Adopt this dynamic plan to maximize net profit while maintaining a {fill_rate:.0%} service level."
    )
    return rec_text

def main():
    parser = argparse.ArgumentParser(description='Generate Inventory Report')
    parser.add_argument('--store_id', required=True, help='Store ID')
    parser.add_argument('--product_id', required=True, help='Product ID')
    parser.add_argument('--time_range', default='7d', help='Time Range')
    parser.add_argument('--output', required=True, help='Output PDF path')
    parser.add_argument('--forecast_csv', required=True, help='Path to forecast CSV')
    
    args = parser.parse_args()
    
    print(f"Generating report for Store {args.store_id}, Product {args.product_id} (7-Day Backtest)...")
    
    SIM_DAYS = 7
    
    # 1. Load Ground Truth (May 2024 Backtest)
    demand_full, dates_full_str = load_ground_truth(args.store_id, args.product_id, month=5)
    
    if not demand_full:
        print("Error: No Ground Truth found for May 2024. Cannot run Backtest.")
        return # Exit if no ground truth

    print(f"Backtest Mode: Using May 2024 Ground Truth ({len(demand_full)} days).")
    
    # 2. Load Forecast
    # Preferred: optim_final_forecast.csv (List)
    # The load_forecast_data function returns a LIST (now updated) or Dict.
    # Let's verify load_forecast_data returns a list for optim_final_forecast.
    forecast_raw = load_forecast_data(args.forecast_csv, args.store_id, args.product_id)
    
    forecast_series = []
    
    # Normalize Forecast to List
    if isinstance(forecast_raw, list):
         forecast_series = forecast_raw
    elif isinstance(forecast_raw, dict):
         # If dict {date: qty}, try to align with dates_full_str
         for d_str in dates_full_str:
             d_ts = pd.to_datetime(d_str)
             forecast_series.append(forecast_raw.get(d_ts, 0)) # Default 0 if missing
    else:
         forecast_series = [0] * len(demand_full)

    # 3. Align Data (First 7 Days)
    demand = demand_full[:SIM_DAYS]
    dates = dates_full_str[:SIM_DAYS]
    
    if forecast_series:
        forecast = forecast_series[:SIM_DAYS]
        # Pad if less than 7
        if len(forecast) < SIM_DAYS:
             forecast += [forecast[-1]] * (SIM_DAYS - len(forecast))
    else:
        forecast = [0] * SIM_DAYS # Zero forecast if missing

    # 4. Define Strategies & Config
    strategies = {
        "Rule-Based": RuleBasedStrategy(min_stock=20, max_stock=50),
        "Math-Based": MathBasedStrategy(uncertainty_factor=0.2),
        "AI-DDMRP": AIDDMRPStrategy(variability_factor=0.25)
    }
    
    sim_config = {
        "LEAD_TIME": settings.LEAD_TIME,
        "HOLDING_COST": settings.HOLDING_COST,
        "SHORTAGE_COST": settings.SHORTAGE_COST,
        "COST": settings.COST,
        "PRICE": settings.PRICE,
        "SHELF_LIFE": settings.SHELF_LIFE
    }

    # --- DEBUG PRINTS ---
    print(f"DEBUG: Report Demand: {demand}")
    print(f"DEBUG: Rule-Based Params: Min={strategies['Rule-Based'].min_stock}, Max={strategies['Rule-Based'].max_stock}")
    print(f"DEBUG: Sim Config: {sim_config}")
    # --------------------

    # 5. Run Simulations
    results_summary = []
    daily_results_dict = {}
    initial_stock = 30 
    
    for name, strategy in strategies.items():
        sim = Simulator(strategy, initial_stock=initial_stock, config=sim_config)
        df_res = sim.run(demand, forecast)
        
        df_res['date'] = dates
        daily_results_dict[name] = df_res
        
        summary = calculate_summary(df_res)
        summary['Strategy'] = name
        
        summary['Purchase Cost'] = df_res['cost_purchase'].sum()
        summary['Holding Cost'] = df_res['cost_holding'].sum()
        summary['Shortage Cost'] = df_res['cost_shortage'].sum()
        summary['Spoilage Cost'] = df_res['cost_spoilage'].sum()
        
        sold_units = sum(demand) - summary['Total Shortage']
        revenue = sold_units * sim_config["PRICE"]
        summary['Profit'] = revenue - summary['Total Cost']
        
        results_summary.append(summary)

    # 6. Visualization
    output_dir = os.path.dirname(args.output)
    visualizer = Visualizer(output_dir=output_dir)
    visualizer.plot_inventory_comparison(daily_results_dict)
    visualizer.plot_cost_structure(results_summary)
    
    image_paths = {
        'inventory_chart': os.path.join(output_dir, 'inventory_comparison.png'),
        'cost_chart': os.path.join(output_dir, 'cost_structure.png')
    }

    # 7. Generate PDF
    df_compare = pd.DataFrame(results_summary)
    rec_text = generate_recommendation_en(df_compare, sim_config)
    
    # Prepare Forecast Table Data (Day, Forecast, Demand)
    forecast_table = []
    for i, (f, d) in enumerate(zip(forecast, demand)):
        forecast_table.append({"Day": dates[i], "Forecast": f"{f:.1f}", "Actual Demand": f"{d}"})

    gen = ReportGenerator(store_id=args.store_id, product_id=args.product_id, date_range=f"Next {SIM_DAYS} Days")
    gen.generate_pdf(results_summary, rec_text, image_paths, forecast_table, output_path=args.output)
    
    print(f"SUCCESS:{args.output}")

if __name__ == "__main__":
    main()
