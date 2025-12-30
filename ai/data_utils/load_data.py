import pandas as pd
import numpy as np
import torch
from torch.utils.data import Dataset
from sklearn.preprocessing import StandardScaler


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


def load_and_preprocess_data(data_path, time_encoded=True, input_len=480, target_len=112, horizon=90):
    data = pd.read_csv(data_path)
    data = data.sort_values(by=['store_id', 'product_id', 'dt'])
    type = data_path.split('/')[-1][:-4]
    if type == 'imputed_data':
        data['hours_sale'] = data['hours_sale'].map(lambda x: x[1:-1].split(', '))
    else:
        data['hours_sale'] = data['hours_sale'].map(lambda x: x[1:-1].replace('\n', '').split())
    data['dt'] = pd.to_datetime(data['dt'])
    data['dayofweek'] = data['dt'].dt.dayofweek
    data['day'] = data['dt'].dt.day
    
    numerical_features = ['discount', 'precpt', 'avg_temperature', 'avg_humidity', 'avg_wind_level']
    binary_features = ['holiday_flag', 'activity_flag']
    time_features = ['dayofweek', 'day'] if time_encoded else []
    
    series_num = data.shape[0] // horizon
    
    hours_sale = np.array(data['hours_sale'].tolist(), dtype=float)
    hours_sale = hours_sale.reshape(series_num, horizon, 24)[..., 6:22]
    
    numerical_data = data[numerical_features].values.astype(float)
    scaler = StandardScaler()
    numerical_normalized = scaler.fit_transform(numerical_data)
    
    if time_encoded:
        time_data = data[time_features].values.astype(float)
        time_data[:, 0] = time_data[:, 0] / 6
        time_data[:, 1] = (time_data[:, 1] - 1) / 30
    else:
        time_data = np.empty((numerical_data.shape[0], 0))
    
    binary_data = data[binary_features].values.astype(float)
    features_combined = np.concatenate([numerical_normalized, binary_data, time_data], axis=1)
    features = features_combined.reshape(series_num, horizon, -1)
    
    hours_sale = np.expand_dims(hours_sale, axis=-1)
    features = np.expand_dims(features, axis=2)
    features = np.broadcast_to(features, (series_num, horizon, hours_sale.shape[2], features.shape[-1]))
    hour_encoding = np.broadcast_to(np.arange(16)[None, None, :, None] / 15, (series_num, horizon, 16, 1))
    
    ds = np.concatenate([features, hour_encoding, hours_sale], axis=-1)
    ds = ds.reshape(series_num, horizon * 16, -1)
    
    del data, numerical_data, numerical_normalized, time_data
    del binary_data, features_combined, features, hour_encoding, hours_sale
    
    dataset = TimeSeriesDataset(ds, input_len=input_len, target_len=target_len)
    return dataset, scaler
