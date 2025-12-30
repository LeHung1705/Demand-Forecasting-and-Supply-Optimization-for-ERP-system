import torch
import torch.nn as nn

class LSTMForecastNet(nn.Module):
    """Mô phỏng SAP IBP Demand Sensing (LSTM/ML-based)"""
    def __init__(self, input_size=1, hidden_size=64, num_layers=2, output_size=1):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, output_size)

    def forward(self, x):
        out, _ = self.lstm(x)
        out = self.fc(out[:, -1, :])  # dùng hidden cuối để dự báo
        return out.unsqueeze(1)