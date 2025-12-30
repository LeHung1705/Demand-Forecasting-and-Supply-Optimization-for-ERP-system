"""Baseline Models for Demand Forecasting"""

import torch
import torch.nn as nn
from typing import Optional, Literal, Tuple, Any


def get_baseline_model(model_name: str, **kwargs) -> Any:
    models = {
        'naive': get_naive_model,
        'moving_average': get_moving_average_model,
        'exponential_smoothing': get_exponential_smoothing_model,
        'arima': get_arima_model,
        'lstm': get_lstm_model
    }
    
    model_fn = models.get(model_name.lower())
    if not model_fn:
        raise ValueError(f"Unknown model: {model_name}. Choose from: {list(models.keys())}")
    
    return model_fn(**kwargs)


def get_naive_model(strategy: Literal['last', 'mean', 'drift'] = 'last',
                    window_length: Optional[int] = None,
                    sp: int = 1):
    from sktime.forecasting.naive import NaiveForecaster
    return NaiveForecaster(strategy=strategy, window_length=window_length, sp=sp)


def get_moving_average_model(window_length: int = 7, sp: int = 1):
    from sktime.forecasting.naive import NaiveForecaster
    return NaiveForecaster(strategy='mean', window_length=window_length, sp=sp)


def get_exponential_smoothing_model(
    trend: Optional[Literal['add', 'mul']] = None,
    damped_trend: bool = False,
    seasonal: Optional[Literal['add', 'mul']] = None,
    seasonal_periods: Optional[int] = None,
    **kwargs
):
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    
    return lambda endog: ExponentialSmoothing(
        endog=endog,
        trend=trend,
        damped_trend=damped_trend,
        seasonal=seasonal,
        seasonal_periods=seasonal_periods,
        **kwargs
    )


def get_arima_model(
    order: Tuple[int, int, int] = (1, 1, 1),
    seasonal_order: Tuple[int, int, int, int] = (0, 0, 0, 0),
    trend: Optional[str] = None,
    **kwargs
):
    from statsmodels.tsa.arima.model import ARIMA
    
    return lambda endog: ARIMA(
        endog=endog,
        order=order,
        seasonal_order=seasonal_order,
        trend=trend,
        **kwargs
    )


class LSTMBaseline(nn.Module):
    def __init__(self, input_size: int = 1, hidden_size: int = 64,
                 num_layers: int = 2, output_size: Optional[int] = None,
                 dropout: float = 0.1):
        super().__init__()
        
        self.output_size = output_size or input_size
        
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0
        )
        
        self.fc = nn.Linear(hidden_size, self.output_size)
        
    def forward(self, x: torch.Tensor, n_ahead: int = 1) -> torch.Tensor:
        _, (hidden, cell) = self.lstm(x)
        
        predictions = []
        current_input = x[:, -1:, :]
        current_hidden, current_cell = hidden, cell
        
        for _ in range(n_ahead):
            lstm_out, (current_hidden, current_cell) = self.lstm(
                current_input, (current_hidden, current_cell)
            )
            pred = self.fc(lstm_out)
            predictions.append(pred)
            current_input = pred
        
        return torch.cat(predictions, dim=1)


def get_lstm_model(input_size: int = 1, hidden_size: int = 64,
                   num_layers: int = 2, output_size: Optional[int] = None,
                   dropout: float = 0.1) -> LSTMBaseline:
    return LSTMBaseline(input_size, hidden_size, num_layers, output_size, dropout)