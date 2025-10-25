from torch.utils.data import Dataset, DataLoader
import pandas as pd
from sklearn.preprocessing import StandardScaler
from datasets import load_dataset
import numpy as np

class Dataset_Custom(Dataset):
    def __init__(self, flag='train', size=None, total_seq_len=90, data_path=None, target='sale_amount', scale=True, train_only=False):
        self.total_seq_len = total_seq_len
        if size == None:
            self.seq_len = 30
            self.pred_len = 7
        else:
            self.seq_len = size[0]
            self.pred_len = size[1]
        # init
        assert flag in ['train', 'test', 'val']
        type_map = {'train': 0, 'val': 1, 'test': 2}
        self.set_type = type_map[flag]

        self.target = target
        self.scale = scale
        self.train_only = train_only

        self.data_path = data_path
        self.__read_data__()

    def __read_data__(self):
        self.scaler = StandardScaler()
        if self.data_path==None:
            dataset = load_dataset("Dingdong-Inc/FreshRetailNet-50K")
            df = dataset['train'].to_pandas()
        else:
            df = pd.read_parquet(self.data_path)

        df = df.rename(columns={'dt': 'date'})
        df = df.sort_values(by=['store_id', 'product_id', 'date'])
        cols = ['discount', 'holiday_flag', 'precpt', 'avg_temperature', 'avg_humidity', 'avg_wind_level', self.target]
        df = df[cols]
        # print(cols)
        num_train = int(self.total_seq_len * 0.7)
        num_test = int(self.total_seq_len * 0.2)
        num_vali = self.total_seq_len - num_train - num_test
        border1s = [0, num_train - self.seq_len, self.total_seq_len - num_test - self.seq_len]
        border2s = [num_train, num_train + num_vali, self.total_seq_len]
        border1 = border1s[self.set_type]
        border2 = border2s[self.set_type]
        self.interval = border2 - border1


        if self.scale:
            train_data = []
            for i in range(0, len(df), self.total_seq_len):
                unit = df.iloc[i:i + self.total_seq_len]
                subset = unit.iloc[border1s[0]:border2s[0]]
                train_data.append(subset)
            train_data = pd.concat(train_data, axis=0, ignore_index=True)
            self.scaler.fit(train_data.values)
            data = self.scaler.transform(df.values)
        else:
            data = df.values

        data_split = []
        for i in range(0, len(data), self.total_seq_len):
            unit = data[i:i + self.total_seq_len]
            subset = unit[border1:border2]
            data_split.append(subset)
        data_split = np.concatenate(data_split, axis=0)
        self.data_x = data_split
        self.data_y = data_split

    def __getitem__(self, index):
        seq_id = index // (self.interval - self.seq_len - self.pred_len + 1)
        seq_idx = index % (self.interval - self.seq_len - self.pred_len + 1)
        s_begin = seq_id * self.interval + seq_idx
        s_end = s_begin + self.seq_len
        r_begin = s_end
        r_end = r_begin + self.pred_len
        seq_x = self.data_x[s_begin:s_end]
        seq_y = self.data_y[r_begin:r_end][-1]
        return seq_x, seq_y

    def __len__(self):
        return (self.interval - self.seq_len - self.pred_len + 1) * (len(self.data_x) // self.interval)

    def inverse_transform(self, data):
        return self.scaler.inverse_transform(data)