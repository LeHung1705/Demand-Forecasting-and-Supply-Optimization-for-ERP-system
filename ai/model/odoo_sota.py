import torch
import torch.nn as nn

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