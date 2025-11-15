import torch
import torch.nn as nn
import torch.nn.functional as F
from statsmodels.tsa.arima.model import ARIMA
import numpy as np


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
    def __init__(self, alpha=0.5):
        super().__init__()
        self.alpha = alpha

    def forward(self, x):
        # x: (batch, seq_len, 1)
        batch_size, seq_len, features = x.shape
        y = x[:, 0, :]  # Khởi tạo với giá trị đầu tiên
        
        for t in range(1, seq_len):
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
        batch_size, seq_len, features = x.shape
        
        if seq_len < self.window_size:
            return x.mean(dim=1, keepdim=True)
        
        # Lấy window cuối cùng
        last_window = x[:, -self.window_size:, :]
        sma = last_window.mean(dim=1, keepdim=True)
        
        return sma

# ==========================
# 🤖 SAP OPTIMIZED — LSTM Forecast Model
# ==========================
class LSTMForecastNet(nn.Module):
    """Mô phỏng SAP IBP Demand Sensing (LSTM/ML-based)"""
    def __init__(self, input_size=1, hidden_size=64, num_layers=2, output_size=1, dropout=0.2):
        super().__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        
        self.lstm = nn.LSTM(
            input_size, 
            hidden_size, 
            num_layers, 
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0
        )
        self.fc = nn.Linear(hidden_size, output_size)

    def forward(self, x):
        # x: (batch, seq_len, input_size)
        out, (h_n, c_n) = self.lstm(x)
        
        # Dùng hidden state cuối để dự báo
        out = self.fc(out[:, -1, :])  # (batch, output_size)


# ==========================
# 📊 ARIMA - Statistical Model
# ==========================
def arima_forecast(x, p=1, d=1, q=0, steps=1):
    """
    ARIMA forecast function
    
    Args:
        x: numpy array hoặc tensor (batch, seq_len) hoặc (seq_len,)
        p, d, q: ARIMA parameters
        steps: số bước dự báo
    
    Returns:
        predictions: numpy array (batch, steps) hoặc (steps,)
    """
    is_tensor = torch.is_tensor(x)
    device = x.device if is_tensor else None
    
    if is_tensor:
        x_np = x.detach().cpu().numpy()
    else:
        x_np = x
    
    # Xử lý batch
    if x_np.ndim == 1:
        x_np = x_np.reshape(1, -1)
        squeeze_output = True
    else:
        squeeze_output = False
    
    preds = []
    for seq in x_np:
        try:
            model = ARIMA(seq, order=(p, d, q))
            fitted = model.fit()
            yhat = fitted.forecast(steps=steps)
        except Exception as e:
            # Fallback: dùng giá trị cuối
            yhat = np.full(steps, seq[-1])
        preds.append(yhat)
    
    preds = np.array(preds)
    
    if squeeze_output:
        preds = preds.squeeze(0)
    
    if is_tensor:
        preds = torch.tensor(preds, dtype=x.dtype, device=device)
    
    return preds
        