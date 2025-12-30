import torch
import torch.nn as nn

class SimpleAverageNet(nn.Module):
    """Mô phỏng Odoo default: trung bình toàn kỳ"""
    def __init__(self):
        super().__init__()

    def forward(self, x):
        # x: (batch, seq_len, features)
        return x.mean(dim=1, keepdim=True)