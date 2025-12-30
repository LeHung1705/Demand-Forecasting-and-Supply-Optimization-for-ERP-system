import torch
import torch.nn as nn

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