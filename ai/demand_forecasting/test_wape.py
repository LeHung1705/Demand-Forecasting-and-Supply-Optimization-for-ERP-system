import numpy as np
import torch
import sys
import os
import pandas as pd
from tqdm import tqdm
from sklearn.preprocessing import StandardScaler
from torch.utils.data import Dataset

# Add project root to sys.path
sys.path.append(os.getcwd())

from model.dlinear import Model

class TimeSeriesDataset(Dataset):
    def __init__(self, data, input_len, target_len):
        self.data = torch.from_numpy(data).float()
        self.input_len = input_len
        self.target_len = target_len
        self.total_len = input_len + target_len
        
        self.indices = []
        for i in range(data.shape[0]):
            n_seqs = data.shape[1] - self.total_len + 1
            if n_seqs > 0:
                self.indices.extend([(i, start) for start in range(n_seqs)])
    
    def __len__(self):
        return len(self.indices)
    
    def __getitem__(self, idx):
        series_idx, start = self.indices[idx]
        seq = self.data[series_idx, start:start + self.total_len]
        x = seq[:self.input_len]
        y_full = seq[self.input_len:]
        x_dec = y_full[:, :-1]
        y = y_full[:, -1:]
        return x, x_dec, y

def compute_daily_wape(y_true, y_pred, hours_per_day=16, eps=1e-8):
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    if y_true.ndim == 3:
        y_true = y_true[..., -1]
        y_pred = y_pred[..., -1]
    
    num_days = y_true.shape[1] // hours_per_day
    y_true_daily = y_true.reshape(-1, num_days, hours_per_day).sum(axis=2)
    y_pred_daily = y_pred.reshape(-1, num_days, hours_per_day).sum(axis=2)
    return 100 * np.sum(np.abs(y_true_daily - y_pred_daily)) / (np.sum(np.abs(y_true_daily)) + eps)

def load_data_flexible(data_path, input_len=480, target_len=112, horizon=90, sample_percent=1.0):
    """
    Load data with configurable sample percentage.
    """
    if sample_percent < 1.0:
        print(f"--- VERSION 1: Loading {sample_percent*100}% of data (Memory Efficient) ---")
    else:
        print(f"--- VERSION 2: Loading 100% of data (Full Evaluation) ---")
        
    try:
        data = pd.read_csv(data_path)
        if sample_percent < 1.0:
            cutoff = int(len(data) * (1 - sample_percent))
            data = data.iloc[cutoff:].copy()
        print(f"Data rows: {len(data)}")
    except Exception as e:
        print(f"Error loading CSV: {e}")
        return None

    data = data.sort_values(by=['store_id', 'product_id', 'dt'])
    
    if isinstance(data['hours_sale'].iloc[0], str):
        data['hours_sale'] = data['hours_sale'].map(lambda x: x.replace('[', '').replace(']', '').replace('\n', ''))
        data['hours_sale'] = data['hours_sale'].map(lambda x: [float(i) for i in x.split(',') if i.strip()])

    data['dt'] = pd.to_datetime(data['dt'])
    data['dayofweek'] = data['dt'].dt.dayofweek
    data['day'] = data['dt'].dt.day
    
    numerical_features = ['discount', 'precpt', 'avg_temperature', 'avg_humidity', 'avg_wind_level']
    binary_features = ['holiday_flag', 'activity_flag']
    time_features = ['dayofweek', 'day']
    
    series_num = data.shape[0] // horizon
    if series_num == 0:
        series_num = 1
        limit = (len(data) // horizon) * horizon
        data = data.iloc[:limit]
        series_num = len(data) // horizon

    data = data.iloc[:series_num * horizon]
    
    hours_sale = np.array(data['hours_sale'].tolist(), dtype=float)
    hours_sale = hours_sale.reshape(series_num, horizon, -1)
    if hours_sale.shape[2] == 24:
        hours_sale = hours_sale[..., 6:22]

    numerical_data = data[numerical_features].values.astype(float)
    scaler = StandardScaler()
    numerical_normalized = scaler.fit_transform(numerical_data)
    
    time_data = data[time_features].values.astype(float)
    time_data[:, 0] = time_data[:, 0] / 6
    time_data[:, 1] = (time_data[:, 1] - 1) / 30
    
    binary_data = data[binary_features].values.astype(float)
    features_combined = np.concatenate([numerical_normalized, binary_data, time_data], axis=1)
    
    features = features_combined.reshape(series_num, horizon, -1)
    hours_sale = np.expand_dims(hours_sale, axis=-1)
    features = np.expand_dims(features, axis=2)
    features = np.broadcast_to(features, (series_num, horizon, hours_sale.shape[2], features.shape[-1]))
    
    hour_encoding = np.broadcast_to(np.arange(16)[None, None, :, None] / 15, (series_num, horizon, 16, 1))
    
    ds = np.concatenate([features, hour_encoding, hours_sale], axis=-1)
    ds = ds.reshape(series_num, horizon * 16, -1)
    
    dataset = TimeSeriesDataset(ds, input_len=input_len, target_len=target_len)
    return dataset

def main():
    class Config:
        def __init__(self):
            self.data_path = 'data/imputed_data.csv'
            self.seq_len = 480
            self.pred_len = 112
            self.enc_in = 11
            self.dec_in = 10
            self.use_decoder = True
            self.individual = True
            self.dropout = 0.1

    configs = Config()
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    # =========================================================================
    # CHOOSE DATA VERSION HERE:
    # =========================================================================
    
    # --- VERSION 1: LOAD 5% DATA (Fast, safe for low RAM) ---
    dataset = load_data_flexible(configs.data_path, sample_percent=0.05)
    
    # --- VERSION 2: LOAD 100% DATA (Full analysis, requires high RAM) ---
    # dataset = load_data_flexible(configs.data_path, sample_percent=1.0)
    
    # =========================================================================

    if dataset is None: return

    model = Model(configs)
    model.to(device)
    ckpt_path = 'demand_forecasting/checkpoints/imputed_decoder/best_dlinear_model.pth'
    
    if os.path.exists(ckpt_path):
        model.load_state_dict(torch.load(ckpt_path, map_location=device))
    else:
        print("WAPE_RESULT: 999.0")
        return

    model.eval()
    all_predictions, all_targets = [], []
    with torch.no_grad():
        max_samples = 2000
        for i in tqdm(range(min(len(dataset), max_samples)), desc="Testing"):
            x, x_dec, y = dataset[i]
            output = model(x.unsqueeze(0).to(device), x_dec.unsqueeze(0).to(device))
            all_predictions.append(output.squeeze(0).cpu().numpy())
            all_targets.append(y.squeeze(0).cpu().numpy())

    wape = compute_daily_wape(np.array(all_targets), np.array(all_predictions))
    print(f"WAPE_RESULT: {wape}")

if __name__ == '__main__':
    main()
