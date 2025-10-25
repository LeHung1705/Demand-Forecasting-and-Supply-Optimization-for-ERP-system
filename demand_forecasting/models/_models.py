import torch
import torch.nn as nn

# ==========================
# 🧮 ODOO BASIC — Simple Average
# ==========================
class SimpleAverageNet(nn.Module):
    """Mô phỏng Odoo default: trung bình toàn kỳ"""
    def __init__(self):
        super().__init__()

    def forward(self, x):
        # x: (batch, seq_len, features)
        return x.mean(dim=1, keepdim=True)


# ==========================
# 🔮 ODOO OPTIMIZED — Exponential Smoothing
# ==========================
class ExponentialSmoothingNet(nn.Module):
    """Mô phỏng Odoo Demand Forecasting App (Exponential Smoothing)"""
    def __init__(self):
        super().__init__()
        self.alpha = nn.Parameter(torch.tensor(0.5))  # hệ số làm mượt

    def forward(self, x):
        # x: (batch, seq_len, 1)
        y = x[:, 0, :]
        for t in range(1, x.size(1)):
            y = self.alpha * x[:, t, :] + (1 - self.alpha) * y
        return y.unsqueeze(1)


# ==========================
# 🏢 SAP BASIC — Simple Moving Average
# ==========================
class SimpleMovingAverageNet(nn.Module):
    """Mô phỏng SAP IBP default: Simple Moving Average"""
    def __init__(self, window_size=3):
        super().__init__()
        self.window_size = window_size

    def forward(self, x):
        # x: (batch, seq_len, 1)
        sma = []
        for t in range(self.window_size, x.size(1) + 1):
            window = x[:, t - self.window_size:t, :].mean(dim=1)
            sma.append(window)
        sma = torch.stack(sma, dim=1)
        return sma[:, -1:, :]  # trả về dự báo cuối


# ==========================
# 🤖 SAP OPTIMIZED — LSTM Forecast Model
# ==========================
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
