
import sys
import os
import warnings
import pandas as pd
import numpy as np
import torch
import argparse
from sklearn.preprocessing import StandardScaler

# Add the 'ai' directory to sys.path so we can import modules from it
# We'll calculate paths relative to this file
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# backend/app/utils -> backend/app -> backend -> root -> ai
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", ".."))
AI_DIR = os.path.join(PROJECT_ROOT, "ai")
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))

sys.path.append(AI_DIR)

# Now we can import from ai
try:
    from data_utils.load_data import load_and_preprocess_data
    from model.baseline_models import get_baseline_model
    from model.dlinear import Model
except ImportError as e:
    print(f"Error importing AI modules: {e}")
    print(f"sys.path: {sys.path}")
    sys.exit(1)

warnings.filterwarnings('ignore')

# Define paths dynamically
DATA_PATH = os.path.join(BACKEND_DIR, "app", "data", "imputed_data.csv")
CKPT_DIR = os.path.join(AI_DIR, "demand_forecasting", "checkpoints")
OUTPUT_PATH = os.path.join(BACKEND_DIR, "app", "data")

def get_forecast_data(data: pd.DataFrame, start_day: int, month: int, year: int, days_ahead: int = 7, use_decoder=True) -> pd.DataFrame:
    forecast_data = data.copy()
    identity = forecast_data[['store_id', 'product_id']].drop_duplicates().reset_index(drop=True)
    forecast_data['dt'] = pd.to_datetime(forecast_data['dt'])
    previous_date = pd.Timestamp(year=year, month=month, day=start_day) - pd.Timedelta(days=30)
    start_date = pd.Timestamp(year=year, month=month, day=start_day)
    end_date   = start_date + pd.Timedelta(days=days_ahead)

    if use_decoder:
        forecast_data = forecast_data[
            (forecast_data['dt'] >= previous_date) &
            (forecast_data['dt'] < end_date)
        ]
    else:
        forecast_data = forecast_data[
         (forecast_data['dt'] >= previous_date) &
         (forecast_data['dt'] < start_date)
        ]
    return forecast_data, start_date, identity


def get_torch_forecast_data(forecast_data, use_decoder=True):
    horizon = 37 if use_decoder else 30
    window_size = 30 * 16

    forecast_data['hours_sale'] = forecast_data['hours_sale'].map(
        lambda x: x[1:-1].replace("'", "").split(', ') # Handle potential extra quotes/formatting
    )
    
    forecast_data['dayofweek'] = forecast_data['dt'].dt.dayofweek
    forecast_data['day'] = forecast_data['dt'].dt.day

    numerical_features = [
        'discount', 'precpt',
        'avg_temperature', 'avg_humidity', 'avg_wind_level'
    ]
    binary_features = ['holiday_flag', 'activity_flag']
    time_features = ['dayofweek', 'day']
    
    for col in numerical_features:
        forecast_data[col] = pd.to_numeric(forecast_data[col], errors='coerce').fillna(0)
    
    total_rows = len(forecast_data)
    if total_rows == 0:
        raise ValueError("No data available for the selected range.")

    # Calculate series_num dynamically
    # The original script assumed 50000 series. We must adapt to the actual data.
    # We assume complete data for each series for the given time range.
    # The dataframe is expected to be stacked: (Series 1, Time 1..T), (Series 2, Time 1..T), ...
    # Or sorted by time then series.
    # Let's check how many unique store_id + product_id combos we have in the input
    # But wait, the reshaping logic assumes a specific order.
    # The original logic: forecast_data['hours_sale'].tolist() -> flatten -> reshape(series_num, horizon, 24)
    # This implies the data is sorted such that each 'series' (store-product) has 'horizon' rows.
    
    series_num = total_rows // horizon

    hours_sale = np.array(
        forecast_data['hours_sale'].tolist(),
        dtype=float
    )
    
    try:
        hours_sale = hours_sale.reshape(series_num, horizon, 24)[..., 6:22]
    except ValueError as e:
        print(f"Reshape error: {e}. Data length: {total_rows}, Horizon: {horizon}, Calculated Series: {series_num}")
        raise

    numerical_data = forecast_data[numerical_features].values.astype(float)
    scaler = StandardScaler()
    numerical_normalized = scaler.fit_transform(numerical_data)

    time_data = forecast_data[time_features].values.astype(float)
    time_data[:, 0] = time_data[:, 0] / 6
    time_data[:, 1] = (time_data[:, 1] - 1) / 30

    binary_data = forecast_data[binary_features].values.astype(float)

    features_combined = np.concatenate(
        [numerical_normalized, binary_data, time_data],
        axis=1
    )
    features = features_combined.reshape(series_num, horizon, -1)

    hours_sale = np.expand_dims(hours_sale, axis=-1)
    features = np.expand_dims(features, axis=2)
    features = np.broadcast_to(
        features,
        (series_num, horizon, hours_sale.shape[2], features.shape[-1])
    )

    hour_encoding = np.broadcast_to(
        np.arange(16)[None, None, :, None] / 15,
        (series_num, horizon, 16, 1)
    )

    ds = np.concatenate(
        [features, hour_encoding, hours_sale],
        axis=-1
    )
    ds = ds.reshape(series_num, horizon * 16, -1)

    n_features = ds.shape[-1] - 1

    x = torch.tensor(ds[:, :window_size, :], dtype=torch.float32)
    x_dec = torch.tensor(ds[:, window_size:, :n_features], dtype=torch.float32)
    y = torch.tensor(ds[:, window_size:, -1:], dtype=torch.float32)

    return x, x_dec, y, series_num

class Config:
    def __init__(self, use_decoder=True):
        self.model = 'dlinear'
        self.patience = 5
        self.enable_scheduler = True
        self.seq_len = 480
        self.pred_len = 112
        self.enc_in = 11
        self.dec_in = 10
        self.use_decoder = use_decoder
        self.individual = True

        self.batch_size = 1024
        self.lr = 0.001
        self.epochs = 20
        self.train_ratio = 0.99


def main(args):
    print(f"Loading data from {DATA_PATH}...")
    if not os.path.exists(DATA_PATH):
        print(f"Error: Data file not found at {DATA_PATH}")
        sys.exit(1)

    data = pd.read_csv(DATA_PATH)

    forecast_data, start_date, final_forecast = get_forecast_data(
        data,
        start_day=args.start_day,
        month=args.month,
        year=args.year,
        days_ahead=7,
        use_decoder=args.use_decoder,
    )

    if forecast_data.empty:
        print("No data found for the specified date range.")
        return

    x, x_dec, _, series_num = get_torch_forecast_data(forecast_data, use_decoder=args.use_decoder)

    configs = Config(use_decoder=args.use_decoder)
    model = Model(configs)

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model.to(device)
    
    ckpt_path = os.path.join(CKPT_DIR, "imputed_decoder", "best_dlinear_model.pth")
    if not args.use_decoder:
        ckpt_path = os.path.join(CKPT_DIR, "imputed_no_decoder", "best_dlinear_model.pth")
        
    print(f"Loading model checkpoint from {ckpt_path}...")
    if not os.path.exists(ckpt_path):
         print(f"Error: Checkpoint file not found at {ckpt_path}")
         sys.exit(1)

    state_dict = torch.load(ckpt_path, map_location=device)
    model.load_state_dict(state_dict)
    model.eval()

    print("Running inference...")
    with torch.no_grad():
        x = x.to(device)
        x_dec = x_dec.to(device) if args.use_decoder else None

        output = model(x, x_dec)
        if not configs.use_decoder:
            output = output[:, :, -1:]

    y_pred_hourly = output.squeeze(-1).cpu().numpy()
    # Reshape based on actual series_num
    y_pred_daily = y_pred_hourly.reshape(series_num, 16, -1).sum(axis=1)

    final_forecast['hourly_forecast'] = list(y_pred_hourly)
    final_forecast['daily_forecast'] = list(y_pred_daily)

    str_time = start_date.strftime('%Y%m%d')
    
    # Clean up old forecast files
    if os.path.exists(OUTPUT_PATH):
        for fname in os.listdir(OUTPUT_PATH):
            if fname.startswith("forecast_data_") and fname.endswith(".csv"):
                file_path = os.path.join(OUTPUT_PATH, fname)
                try:
                    os.remove(file_path)
                    print(f"Deleted: {file_path}")
                except Exception as e:
                    print(f"Could not delete {file_path}: {e}")

    output_file = os.path.join(OUTPUT_PATH, f'final_forecast_{str_time}.csv')
    final_forecast.to_csv(output_file, index=False)
    print(f"Saved forecast to {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser("Run DLinear Forecast Wrapper")

    parser.add_argument("--start_day", type=int, required=True)
    parser.add_argument("--month", type=int, required=True)
    parser.add_argument("--year", type=int, required=True)

    parser.add_argument("--use_decoder", action="store_true")
    parser.add_argument("--no_decoder", action="store_false", dest="use_decoder")
    parser.set_defaults(use_decoder=True)

    args = parser.parse_args()
    main(args)
