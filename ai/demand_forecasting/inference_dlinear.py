#!/usr/bin/env python3
import argparse
import sys
import warnings
import os
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import torch
from sklearn.preprocessing import StandardScaler

sys.path.append('/home/quang_ai/Demand-Forecasting-and-Supply-Optimization-for-ERP-system/ai')

from data_utils.load_data import load_and_preprocess_data
from model.baseline_models import get_baseline_model
from model.dlinear import Model

DATA_PATH = "/home/quang_ai/Demand-Forecasting-and-Supply-Optimization-for-ERP-system/ai/data/imputed_data.csv"
CKPT_PATH = "/home/quang_ai/Demand-Forecasting-and-Supply-Optimization-for-ERP-system/ai/demand_forecasting/checkpoints/imputed_decoder/best_dlinear_model.pth"
OUTPUT_PATH = "/home/quang_ai/Demand-Forecasting-and-Supply-Optimization-for-ERP-system/backend/app/data"

def get_forecast_data(data: pd.DataFrame, start_day: int, month: int, year: int, days_ahead: int = 7, use_decoder=True) -> pd.DataFrame:
    # forecast_data = data[(data['store_id'] == store_id) & (data['product_id'] == product_id) ].copy()
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
    # arguments
    series_num = 50000
    horizon = 37 if use_decoder else 30
    window_size = 30 * 16

    forecast_data['hours_sale'] = forecast_data['hours_sale'].map(
        lambda x: x[1:-1].split(', ')
    )
    forecast_data['dayofweek'] = forecast_data['dt'].dt.dayofweek
    forecast_data['day'] = forecast_data['dt'].dt.day

    numerical_features = [
        'discount', 'precpt',
        'avg_temperature', 'avg_humidity', 'avg_wind_level'
    ]
    binary_features = ['holiday_flag', 'activity_flag']
    time_features = ['dayofweek', 'day']

    hours_sale = np.array(
        forecast_data['hours_sale'].tolist(),
        dtype=float
    )
    hours_sale = hours_sale.reshape(series_num, horizon, 24)[..., 6:22]

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
    # ds = ds.squeeze(0)

    n_features = ds.shape[-1] - 1

    x = torch.tensor(ds[:, :window_size, :], dtype=torch.float32)
    x_dec = torch.tensor(ds[:, window_size:, :n_features], dtype=torch.float32)
    y = torch.tensor(ds[:, window_size:, -1:], dtype=torch.float32)

    return x, x_dec, y

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
    data = pd.read_csv(DATA_PATH)

    forecast_data, start_date, final_forecast = get_forecast_data(
        data,
        start_day=args.start_day,
        month=args.month,
        year=args.year,
        days_ahead=7,
        use_decoder=args.use_decoder,
    )

    x, x_dec, _ = get_torch_forecast_data(forecast_data, use_decoder=args.use_decoder)

    configs = Config(use_decoder=args.use_decoder)
    model = Model(configs)

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model.to(device)
    CKPT_PATH = "/home/quang_ai/Demand-Forecasting-and-Supply-Optimization-for-ERP-system/ai/demand_forecasting/checkpoints/imputed_decoder/best_dlinear_model.pth"
    CKPT_PATH = CKPT_PATH if args.use_decoder else CKPT_PATH.replace('decoder', 'no_decoder')
    state_dict = torch.load(CKPT_PATH, map_location=device)
    model.load_state_dict(state_dict)
    model.eval()

    with torch.no_grad():
        x = x.to(device)
        x_dec = x_dec.to(device) if args.use_decoder else None

        output = model(x, x_dec)
        if not configs.use_decoder:
            output = output[:, :, -1:]

    y_pred_hourly = output.squeeze(-1).cpu().numpy()
    y_pred_daily = y_pred_hourly.reshape(50000, 16, -1).sum(axis=1)

    final_forecast['hourly_forecast'] = list(y_pred_hourly)
    final_forecast['daily_forecast'] = list(y_pred_daily)

    str_time = start_date.strftime('%Y%m%d')
    output_path = OUTPUT_PATH
    for fname in os.listdir(output_path):
        if fname.startswith("forecast_data_") and fname.endswith(".csv"):
            file_path = os.path.join(output_path, fname)
            os.remove(file_path)
            print(f"Deleted: {file_path}")

    final_forecast.to_csv(os.path.join(output_path, f'final_forecast_{str_time}.csv'), index=False)
    print(f"Saved forecast to final_forecast_{str_time}.csv")


if __name__ == "__main__":
    parser = argparse.ArgumentParser("Run DLinear Forecast")

    parser.add_argument("--start_day", type=int, required=True)
    parser.add_argument("--month", type=int, required=True)
    parser.add_argument("--year", type=int, required=True)

    parser.add_argument("--use_decoder", action="store_true")
    parser.add_argument("--no_decoder", action="store_false", dest="use_decoder")
    parser.set_defaults(use_decoder=True)

    args = parser.parse_args()
    main(args)
