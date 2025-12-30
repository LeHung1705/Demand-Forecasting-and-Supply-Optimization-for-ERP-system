from __future__ import annotations

import os
import sys
import json
import subprocess
import ast
import zipfile
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional, Tuple, List, Any, Dict

import pandas as pd
import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from starlette.responses import FileResponse

from app.config import settings

# For PDF and plotting
import matplotlib
matplotlib.use('Agg') # Use non-interactive backend
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from io import BytesIO

router = APIRouter(prefix="/export", tags=["export"])

# --- Constants & Paths ---
PROJECT_ROOT = Path(__file__).resolve().parents[2]  # backend/
AI_DIR = PROJECT_ROOT.parent / "ai"
FORECAST_DIR = Path(settings.DATA_PATH)
INFERENCE_DF_SH = settings.INFERENCE_DF_SH

# Mock Financials (from ai/inventory_optimization_module/configs/settings.py)
BASE_PRICE = 50.0
UNIT_COST = 30.0

class ExportReportRequest(BaseModel):
    store_id: Optional[int] = None
    product_id: Optional[int] = None
    forecast_days: int = Field(7, ge=1, le=7)
    lead_time: int = Field(2, ge=1, le=365)
    service_level: float = Field(0.95, ge=0.5, le=0.999)
    pipeline: str = "forecast_only"

    class Config:
        extra = "ignore"


def _resolve_csv_paths() -> Tuple[Path, Path, Path]:
    observed_csv = Path(settings.CSV_PATH).resolve()
    recovered_csv = Path(settings.CSV_IMPUTED_PATH).resolve()
    tmp_dir = PROJECT_ROOT / "tmp"
    return observed_csv, recovered_csv, tmp_dir


def _run_ai_script(script_rel_path: str, args: List[str], description: str):
    script_full_path = AI_DIR / script_rel_path
    cmd_str = f"source ~/miniconda3/etc/profile.d/conda.sh && conda activate torch-gpu && python '{script_full_path}' {' '.join(args)}"
    print(f"--- {description} ---")
    try:
        subprocess.run(["bash", "-c", cmd_str], cwd=str(PROJECT_ROOT.parent), check=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running {description}: {e}")
        raise HTTPException(status_code=500, detail=f"AI Pipeline failed: {description}")


def _execute_pipeline(pipeline: str):
    if pipeline == "adaptive_recommend":
        _run_ai_script("process_4_controller.py", [], "Adaptive Controller (Process 4)")
    elif pipeline == "train_df_then_forecast":
        _run_ai_script("latent_demand_recovery/impute.py", [], "Imputation")
        _run_ai_script("demand_forecasting/exp/exp_dlinear.py", ["--data_type", "imputed", "--use_decoder"], "Train DLinear")
    elif pipeline == "train_ldr_then_train_df_then_forecast":
        _run_ai_script("data_utils/process_data.py", [], "Process Data")
        _run_ai_script("latent_demand_recovery/exp/timesnet.py", [], "Train TimesNet")
        _run_ai_script("latent_demand_recovery/impute.py", [], "Imputation")
        _run_ai_script("demand_forecasting/exp/exp_dlinear.py", ["--data_type", "imputed", "--use_decoder"], "Train DLinear")


def _run_inference_job(target_date: date, discount: Optional[float] = None, output_fn: Optional[str] = None):
    # Base arguments
    args = [str(target_date.day), str(target_date.month), str(target_date.year)]
    
    # We remove explicit '--no_decoder' here.
    # The inference_dlinear.py script logic:
    # - If discount_override is present -> Forces use_decoder=True to see future features.
    # - If not present -> Defaults to use_decoder=True (or as per script default).
    # If we wanted to force no_decoder for standard forecast, we would pass it,
    # but for simulation we absolutely need decoder.
    # Let's trust the python script's default or internal logic switch.
    # If we want standard forecast to be no_decoder (as it was originally), we should perhaps pass it ONLY if discount is None?
    # Original logic for dashboard was no_decoder.
    
    if discount is None:
        args.append("--no_decoder")
    # else: simulation -> use_decoder implied by script logic or default
    
    if discount is not None:
        args.append(f"--discount_override {discount}")
    if output_fn is not None:
        args.append(f"--output_filename {output_fn}")
    
    cmd_str = f"source ~/miniconda3/etc/profile.d/conda.sh && conda activate torch-gpu && bash '{INFERENCE_DF_SH}' {' '.join(args)}"
    try:
        subprocess.run(["bash", "-c", cmd_str], cwd=str(PROJECT_ROOT.parent), check=True)
    except subprocess.CalledProcessError as e:
        print(f"Inference failed: {e}")


def _load_forecast_df(csv_path: Path) -> pd.DataFrame:
    if not csv_path.exists():
        return pd.DataFrame(columns=["store_id", "product_id", "daily_forecast"])
    df = pd.read_csv(csv_path)
    def parse_list(val):
        try:
            s = str(val).strip()
            if s.startswith("[") and s.endswith("]"): s = s[1:-1]
            return [float(x) for x in s.split() if x]
        except: return []
    df["forecast_list"] = df["daily_forecast"].apply(parse_list)
    return df


def _generate_optimization_pdf(
    output_path: Path,
    req: ExportReportRequest,
    analysis_date: str,
    sim_results: List[Dict[str, Any]],
    best_discount: float
):
    c = canvas.Canvas(str(output_path), pagesize=letter)
    width, height = letter

    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, height - 50, "Demand Forecasting & Profit Optimization Report")
    
    c.setFont("Helvetica", 12)
    c.drawString(50, height - 80, f"Analysis Date: {analysis_date}")
    c.drawString(50, height - 100, f"Target Store: {'All' if req.store_id is None else req.store_id}")
    c.drawString(50, height - 120, f"Target SKU: {'All' if req.product_id is None else req.product_id}")
    
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, height - 160, "Financial Assumptions")
    c.setFont("Helvetica", 12)
    c.drawString(50, height - 180, f"- Base Price: ${BASE_PRICE}")
    c.drawString(50, height - 200, f"- Unit Cost: ${UNIT_COST}")
    c.drawString(50, height - 220, f"- Margin (at 0% discount): ${BASE_PRICE - UNIT_COST} ({(BASE_PRICE-UNIT_COST)/BASE_PRICE*100:.1f}%)")

    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, height - 260, "Discount Scenario Simulation (7-Day Projection)")
    
    y = height - 290
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Scenario")
    c.drawString(150, y, "Total Demand")
    c.drawString(250, y, "Revenue")
    c.drawString(350, y, "Total Profit")
    c.drawString(450, y, "ROI")
    
    for res in sim_results:
        y -= 20
        is_best = res['discount'] == best_discount
        if is_best: c.setFont("Helvetica-Bold", 10)
        else: c.setFont("Helvetica", 10)
        
        c.drawString(50, y, res['label'])
        c.drawString(150, y, f"{res['total_demand']:.1f}")
        c.drawString(250, y, f"${res['revenue']:,.2f}")
        c.drawString(350, y, f"${res['profit']:,.2f}")
        c.drawString(450, y, f"{res['roi']:.1f}%")
        if is_best: c.drawString(520, y, "<-- RECOMMENDED")

    # Charts
    # Create chart in memory
    labels = [r['label'] for r in sim_results]
    profits = [r['profit'] for r in sim_results]
    demands = [r['total_demand'] for r in sim_results]

    fig, ax1 = plt.subplots(figsize=(6, 3.5)) # Reduced height ratio
    ax1.bar(labels, profits, color='skyblue', label='Profit ($)')
    ax1.set_xlabel('Discount Level')
    ax1.set_ylabel('Total Profit ($)', color='blue')
    
    ax2 = ax1.twinx()
    ax2.plot(labels, demands, color='red', marker='o', label='Demand (Units)')
    ax2.set_ylabel('Total Demand (Units)', color='red')
    
    plt.title('Profit vs Demand at Different Discount Levels')
    
    img_data = BytesIO()
    plt.savefig(img_data, format='png', bbox_inches='tight')
    plt.close()
    img_data.seek(0)
    
    # Adjust Chart Position to avoid overlap with table
    # Table ends around height - 370 (Header 290 + 4 rows * 20)
    # Let's start chart at height - 640 with height 240 -> Top at height - 400
    c.drawImage(ImageReader(img_data), 50, height - 640, width=500, height=240)

    # Conclusion
    # Move conclusion down below the chart
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, height - 670, "Optimization Recommendation")
    c.setFont("Helvetica", 12)
    best_res = next(r for r in sim_results if r['discount'] == best_discount)
    c.drawString(50, height - 690, f"Recommended Strategy: {best_res['label']}")
    c.drawString(50, height - 710, f"Expected total profit for the next 7 days: ${best_res['profit']:,.2f}")
    
    c.showPage()
    c.save()


@router.post("/report")
def export_report(req: ExportReportRequest):
    observed_csv, recovered_csv, tmp_dir = _resolve_csv_paths()
    os.makedirs(tmp_dir, exist_ok=True)

    _execute_pipeline(req.pipeline)

    if not observed_csv.exists():
        raise HTTPException(status_code=500, detail="Original data CSV not found.")
    df_obs = pd.read_csv(observed_csv)
    df_obs["dt"] = pd.to_datetime(df_obs["dt"], errors="coerce")
    max_dt = df_obs["dt"].max().date() if not df_obs.empty else date.today()

    discounts = [1.0, 0.9, 0.8, 0.7] # 0%, 10%, 20%, 30%
    labels = ["0% Discount", "10% Discount", "20% Discount", "30% Discount"]
    sim_results = []
    temp_sim_files = []
    default_forecast_df = None

    for disc, label in zip(discounts, labels):
        suffix = f"sim_{int(round((1-disc)*100))}"
        out_fn = f"forecast_{max_dt.strftime('%Y%m%d')}_{suffix}.csv"
        sim_file_path = FORECAST_DIR / out_fn
        
        _run_inference_job(max_dt, discount=disc, output_fn=out_fn)
        temp_sim_files.append(sim_file_path)
        
        df_sim = _load_forecast_df(sim_file_path)
        if req.store_id is not None: df_sim = df_sim[df_sim["store_id"] == req.store_id]
        if req.product_id is not None: df_sim = df_sim[df_sim["product_id"] == req.product_id]
        
        total_demand = df_sim["forecast_list"].apply(lambda x: sum(x[:7])).sum() if not df_sim.empty else 0.0
        sale_price = BASE_PRICE * disc
        revenue = total_demand * sale_price
        profit = total_demand * (sale_price - UNIT_COST)
        roi = (profit / (total_demand * UNIT_COST) * 100) if total_demand > 0 else 0
        
        sim_results.append({"discount": disc, "label": label, "total_demand": total_demand, "revenue": revenue, "profit": profit, "roi": roi})
        if disc == 1.0: default_forecast_df = df_sim.copy()

    best_res = max(sim_results, key=lambda x: x['profit'])
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    pdf_filename = f"Optimization_Analysis_{ts}.pdf"
    csv_filename = f"Raw_Data_{ts}.csv"
    zip_filename = f"Optimization_Report_{ts}.zip"
    pdf_path, csv_path, zip_path = tmp_dir / pdf_filename, tmp_dir / csv_filename, tmp_dir / zip_filename

    try:
        _generate_optimization_pdf(pdf_path, req, str(max_dt), sim_results, best_res['discount'])
        if default_forecast_df is not None and not default_forecast_df.empty:
            default_forecast_df["forecast_mean_daily"] = default_forecast_df["forecast_list"].apply(lambda x: np.mean(x[:7]) if x else 0.0)
            df_obs_f = df_obs if req.store_id is None else df_obs[df_obs["store_id"] == req.store_id]
            if req.product_id is not None: df_obs_f = df_obs_f[df_obs_f["product_id"] == req.product_id]
            sale_col = next((c for c in ["sale_amount", "sales", "value"] if c in df_obs_f.columns), "sale_amount")
            obs_agg = df_obs_f.groupby(["store_id", "product_id"]).agg(observed_sales=(sale_col, "sum")).reset_index()
            summary = pd.merge(obs_agg, default_forecast_df[["store_id", "product_id", "forecast_mean_daily"]], on=["store_id", "product_id"], how="outer").fillna(0)
            summary["safety_stock"] = (summary["forecast_mean_daily"] * 0.2 * req.lead_time).round().astype(int)
            summary["rop"] = (summary["forecast_mean_daily"] * req.lead_time + summary["safety_stock"]).round().astype(int)
            summary["suggested_order"] = summary["rop"].clip(lower=0).astype(int)
            summary["status"] = summary["suggested_order"].apply(lambda x: "Reorder" if x > 0 else "Sufficient")
            out_csv = pd.DataFrame({"Store ID": summary["store_id"].astype(int), "Product ID": summary["product_id"].astype(int), "Observed Sales": summary["observed_sales"].round(2), "Forecast Mean (7d)": summary["forecast_mean_daily"].round(2), "Safety Stock": summary["safety_stock"], "ROP": summary["rop"], "Suggested Order": summary["suggested_order"], "Status": summary["status"]})
            out_csv.to_csv(csv_path, index=False, encoding="utf-8-sig")
        else:
            pd.DataFrame(["No data available"]).to_csv(csv_path, index=False)

        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.write(pdf_path, arcname=pdf_filename)
            zf.write(csv_path, arcname=csv_filename)
    finally:
        for f in temp_sim_files:
            if f.exists(): os.remove(f)
        if pdf_path.exists(): os.remove(pdf_path)
        if csv_path.exists(): os.remove(csv_path)

    return FileResponse(path=str(zip_path), media_type="application/zip", filename=zip_filename)