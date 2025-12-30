# backend/app/routes/optimization.py
from __future__ import annotations

import sys
import os
import uuid
import pandas as pd
import numpy as np
import subprocess
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.services.optimization_service import calculate_optimal_supply
from app.config import settings as app_settings
from app.data.csv_store import CsvDuckStore

# --- AI Module Setup ---
current_file = os.path.abspath(__file__)
backend_app_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_file))) # backend/
repo_root = os.path.dirname(backend_app_dir)
ai_dir = os.path.join(repo_root, "ai")
if ai_dir not in sys.path:
    sys.path.append(ai_dir)

# Import AI modules (wrapped in try-except)
try:
    from inventory_optimization_module.strategies.rule_based import RuleBasedStrategy
    from inventory_optimization_module.strategies.math_based import MathBasedStrategy
    from inventory_optimization_module.strategies.ai_ddmrp import AIDDMRPStrategy
    from inventory_optimization_module.core.simulator import Simulator
    from inventory_optimization_module.analysis.cost_calculator import calculate_summary
    # NEW: Import settings
    from inventory_optimization_module.configs import settings as ai_settings
except ImportError as e:
    print(f"Warning: Could not import AI modules: {e}")

router = APIRouter(prefix="/optimize", tags=["optimization"])

# --- Models ---

class SupplyConstraints(BaseModel):
    budget: float = Field(default=50_000_000, description="Value cap (VND/value)")
    max_inventory: float = Field(default=50_000_000, description="Value cap (because no qty/unit_cost)")
    lead_time: int = Field(default=7, ge=1, le=90)

class OptimizeSupplyRequest(BaseModel):
    time_range: str = Field(default="30d", description="7d|30d|90d")
    store_id: Optional[int] = Field(default=None)
    product_ids: Optional[List[int]] = Field(default=None)
    constraints: SupplyConstraints = Field(default_factory=SupplyConstraints)

class SimulationParams(BaseModel):
    lead_time: int = Field(default=1, ge=1)
    service_level: float = Field(default=0.95, ge=0.0, le=1.0)
    holding_cost: float = Field(default=1.0, ge=0.0)
    shortage_cost: float = Field(default=100.0, ge=0.0)

class RunSimulationRequest(BaseModel):
    store_id: int
    product_id: int
    strategy_type: str = Field(..., description="Rule-Based | Math-Based | AI-DDMRP")
    params: SimulationParams

# --- Helper ---
def get_forecast_from_csv(store_id: int, product_id: int, days: int = 30) -> List[float]:
    data_dir = os.path.join(backend_app_dir, "app", "data")
    # CORRECT: Users requested optim_final_forecast.csv for Simulation Route
    forecast_path = os.path.join(data_dir, "optim_final_forecast.csv")
    if not os.path.exists(forecast_path):
        forecast_path = os.path.join(data_dir, "final_forecast.csv")
    
    if not os.path.exists(forecast_path):
        return [10.0] * days # Fallback

    try:
        df = pd.read_csv(forecast_path)
        df = df[(df['store_id'] == store_id) & (df['product_id'] == product_id)]
        
        if df.empty:
            return [10.0] * days
            
        row = df.iloc[0]
        val_str = row.get('daily_forecast', '')
        if isinstance(val_str, str):
            clean = val_str.replace('[', '').replace(']', '').replace('\n', ' ')
            parts = clean.split()
            forecasts = [float(p) for p in parts if p]
            return forecasts[:days]
        return [10.0] * days
    except Exception as e:
        print(f"Error reading forecast CSV: {e}")
        return [10.0] * days

def get_current_stock(store_id: int, product_id: int) -> int:
    store = CsvDuckStore.instance(app_settings.CSV_PATH, app_settings.DUCKDB_PATH, app_settings.CSV_IMPUTED_PATH)
    rows = store.query(
        """
        SELECT stock_hour6_22_cnt 
        FROM sales 
        WHERE store_id = ? AND product_id = ? 
        ORDER BY dt DESC 
        LIMIT 1
        """, 
        [store_id, product_id]
    )
    if rows:
        return int(rows[0].get('stock_hour6_22_cnt', 0) or 0)
    return 20 # Default

# --- Endpoints ---

@router.post("/simulate")
def run_simulation(payload: RunSimulationRequest):
    # 1. Load Data
    # CORRECT: Default to 7 days as forecast is only 7 days
    forecast = get_forecast_from_csv(payload.store_id, payload.product_id, days=7)
    initial_stock = get_current_stock(payload.store_id, payload.product_id)
    
    # Generate Synthetic Demand
    np.random.seed(42)
    demand = []
    for f in forecast:
        noise = np.random.normal(0, 0.2 * f)
        d = max(0, int(round(f + noise)))
        demand.append(d)

    # 2. Run BASELINE (Rule-Based)
    baseline_strategy = RuleBasedStrategy(min_stock=10, max_stock=30)
    
    # USE CONSTANTS FROM SETTINGS.PY
    baseline_config = {
        "LEAD_TIME": ai_settings.LEAD_TIME,
        "HOLDING_COST": ai_settings.HOLDING_COST,
        "SHORTAGE_COST": ai_settings.SHORTAGE_COST,
        "COST": ai_settings.COST,
        "PRICE": ai_settings.PRICE,
        "SHELF_LIFE": ai_settings.SHELF_LIFE
    }
    
    baseline_sim = Simulator(baseline_strategy, initial_stock=initial_stock, config=baseline_config)
    df_baseline = baseline_sim.run(demand, forecast)
    summary_baseline = calculate_summary(df_baseline)
    baseline_profit = summary_baseline.get("Total Revenue", 0) - summary_baseline.get("Total Cost", 0)

    # 3. Run OPTIMIZED (AI-DDMRP)
    ai_strategy = AIDDMRPStrategy(variability_factor=0.5, lead_time=ai_settings.LEAD_TIME)
    ai_sim = Simulator(ai_strategy, initial_stock=initial_stock, config=baseline_config)
    df_ai = ai_sim.run(demand, forecast)
    summary_ai = calculate_summary(df_ai)
    ai_profit = summary_ai.get("Total Revenue", 0) - summary_ai.get("Total Cost", 0)

    # 4. Recommendation
    first_day = df_ai.iloc[0]
    suggested_qty = int(first_day['order_qty'])
    fill_rate = float(summary_ai.get("Fill Rate", 0)) * 100

    # 5. Response
    dates = [f"Day {i+1}" for i in range(len(df_ai))]
    
    return {
        "recommendation": {
            "order_qty": suggested_qty,
            "projected_profit": round(ai_profit, 2),
            "fill_rate": round(fill_rate, 2),
            "sku": str(payload.product_id)
        },
        "charts": {
            "dates": dates,
            "inventory": df_ai['stock_end'].tolist(),
            "demand": df_ai['demand'].tolist(),
            "forecast": df_ai['forecast'].tolist(),
            "baseline_inventory": df_baseline['stock_end'].tolist()
        },
        "recommendation_meta": {
             "config_used": {
                 "holding_cost": ai_settings.HOLDING_COST,
                 "shortage_cost": ai_settings.SHORTAGE_COST,
                 "shelf_life": ai_settings.SHELF_LIFE
             }
        },
        "comparison": {
            "rule_based_profit": round(baseline_profit, 2),
            "ai_profit": round(ai_profit, 2),
            "improvement": round(ai_profit - baseline_profit, 2)
        }
    }

@router.post("/supply")
def optimize_supply_chain(payload: OptimizeSupplyRequest):
    return calculate_optimal_supply(
        time_range=payload.time_range,
        store_id=payload.store_id,
        product_ids=payload.product_ids,
        constraints=payload.constraints.model_dump(),
    )

@router.post("/report")
def generate_optimization_report(payload: OptimizeSupplyRequest):
    script_path = os.path.join(repo_root, "ai", "inventory_optimization_module", "run_report.py")
    
    if not os.path.exists(script_path):
        raise HTTPException(status_code=500, detail=f"Report script not found at {script_path}")

    # Create a temporary output filename
    output_filename = f"report_{uuid.uuid4()}.pdf"
    output_path = os.path.join(backend_app_dir, "temp_reports", output_filename)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Prepare arguments
    store_id = str(payload.store_id) if payload.store_id else "11"
    product_id = str(payload.product_ids[0]) if payload.product_ids else "267"
    time_range = payload.time_range

    # Find forecast file
    data_dir = os.path.join(backend_app_dir, "app", "data")
    # Use the Backtesting/Optimization Forecast file as requested (May 2024 array data)
    forecast_path = os.path.join(data_dir, "optim_final_forecast.csv")
    
    if not os.path.exists(forecast_path):
        forecast_path = os.path.join(data_dir, "final_forecast.csv")
    if not os.path.exists(forecast_path):
        forecast_path = os.path.join(data_dir, "optim_final_forecast.csv")

    cmd = [
        sys.executable,
        script_path,
        "--store_id", store_id,
        "--product_id", product_id,
        "--time_range", time_range,
        "--output", output_path,
        "--forecast_csv", forecast_path
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        if "SUCCESS:" in result.stdout:
            return FileResponse(
                path=output_path, 
                filename=f"demand_report_{store_id}_{product_id}.pdf",
                media_type='application/pdf'
            )
        else:
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            raise HTTPException(status_code=500, detail="Report generation failed (Script Error)")
    except subprocess.CalledProcessError as e:
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        raise HTTPException(status_code=500, detail=f"Report generation process failed: {e.stderr}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@router.get("/recommendations")
def get_recommendations(
    time_range: str = "30d",
    store_id: Optional[int] = None,
    top_n: int = 20,
):
    res = calculate_optimal_supply(
        time_range=time_range,
        store_id=store_id,
        product_ids=None,
        constraints={"budget": 1e18, "max_inventory": 1e18, "lead_time": 7},
    )
    res["data"] = (res.get("data") or [])[: max(1, min(int(top_n or 20), 200))]
    res.setdefault("meta", {})["top_n"] = int(top_n or 20)
    return res
