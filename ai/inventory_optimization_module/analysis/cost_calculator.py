import pandas as pd

def calculate_summary(df_results: pd.DataFrame) -> dict:
    return {
        "Total Cost": df_results['total_cost'].sum(),
        "Total Revenue": (df_results['demand'] - df_results['shortage']).sum() * 50.0, # Price 50 (hardcoded here or import settings)
        "Total Shortage": df_results['shortage'].sum(),
        "Total Spoilage": df_results['spoiled'].sum(),
        "Avg Stock": df_results['stock_end'].mean(),
        "Fill Rate": 1 - (df_results['shortage'].sum() / df_results['demand'].sum()) if df_results['demand'].sum() > 0 else 1.0
    }
