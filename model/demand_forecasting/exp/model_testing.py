import torch
from torch.utils.data import DataLoader
import numpy as np
import pandas as pd
import time
from sklearn.metrics import mean_absolute_error, mean_squared_error
from xgboost import XGBRegressor
from lightgbm import LGBMRegressor
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.holtwinters import ExponentialSmoothing


def evaluate_model(y_true, y_pred, runtime):
    mae = mean_absolute_error(y_true, y_pred)
    rmse = mean_squared_error(y_true, y_pred, squared=False)
    mape = np.mean(np.abs((y_true - y_pred) / (y_true + 1e-8))) * 100
    return {
        "MAE": mae,
        "RMSE": rmse,
        "MAPE": mape,
        "Runtime (s)": runtime
    }

def batch_generator(loader):
    """Sinh lần lượt từng batch từ DataLoader"""
    for X, y in loader:
        X = X.numpy()
        y = y.numpy()
        if X.ndim == 3:
            X = X.reshape(X.shape[0], -1)  # flatten theo seq_len
        yield X, y


def train_and_evaluate_tree_model(model_class, model_name, train_loader, val_loader, test_loader, **model_params):
    print(f"\nTraining {model_name}...")
    start = time.time()

    # Khởi tạo model
    model = model_class(**model_params)

    # Fit theo batch để tránh tràn RAM
    first_batch = True
    for X_batch, y_batch in batch_generator(train_loader):
        if first_batch:
            model.fit(X_batch, y_batch, verbose=False)
            first_batch = False
        else:
            model.fit(X_batch, y_batch, xgb_model=None, verbose=False)

    # Dự đoán theo batch
    y_true, y_pred = [], []
    for X_batch, y_batch in batch_generator(test_loader):
        preds = model.predict(X_batch)
        y_pred.append(preds)
        y_true.append(y_batch)

    y_pred = np.concatenate(y_pred)
    y_true = np.concatenate(y_true)

    runtime = time.time() - start
    result = evaluate_model(y_true, y_pred, runtime)

    print(f"{model_name} Done in {runtime:.2f}s — MAE={result['MAE']:.4f}, RMSE={result['RMSE']:.4f}")
    return result


def train_and_evaluate_ts_model(model_name, train_loader, test_loader):
    print(f"\nTraining {model_name}...")
    start = time.time()

    # Gom toàn bộ y train / test (ARIMA, ETS chỉ dùng 1D)
    y_train_all, y_test_all = [], []
    for _, y_batch in batch_generator(train_loader):
        y_train_all.append(y_batch)
    for _, y_batch in batch_generator(test_loader):
        y_test_all.append(y_batch)
    y_train = np.concatenate(y_train_all).flatten()
    y_test = np.concatenate(y_test_all).flatten()

    # Huấn luyện và dự đoán
    if model_name == "ARIMA":
        model = ARIMA(y_train, order=(1, 1, 1))
        model_fit = model.fit()
        preds = model_fit.forecast(steps=len(y_test))
    elif model_name == "ETS":
        model = ExponentialSmoothing(y_train, trend="add", seasonal=None)
        model_fit = model.fit()
        preds = model_fit.forecast(len(y_test))
    else:
        raise ValueError("Unsupported time series model")

    runtime = time.time() - start
    result = evaluate_model(y_test, preds, runtime)

    print(f"{model_name} Done in {runtime:.2f}s — MAE={result['MAE']:.4f}, RMSE={result['RMSE']:.4f}")
    return result

def run_experiments(train_loader, val_loader, test_loader):
    results = {}

    results["XGBoost"] = train_and_evaluate_tree_model(
        XGBRegressor,
        "XGBoost",
        train_loader,
        val_loader,
        test_loader,
        n_estimators=300,
        learning_rate=0.05,
        max_depth=6,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=4,
        verbosity=0
    )

    results["LightGBM"] = train_and_evaluate_tree_model(
        LGBMRegressor,
        "LightGBM",
        train_loader,
        val_loader,
        test_loader,
        n_estimators=300,
        learning_rate=0.05,
        num_leaves=31,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=4,
        verbose=-1
    )

    results["ARIMA"] = train_and_evaluate_ts_model("ARIMA", train_loader, test_loader)
    results["ETS"] = train_and_evaluate_ts_model("ETS", train_loader, test_loader)

    df_results = pd.DataFrame(results).T
    print("\nModel Comparison Results:")
    print(df_results)
    df_results.to_csv("model_comparison_results.csv", index=True)
    print("\nSaved results to model_comparison_results.csv")

    return df_results

if __name__ == "__main__":
    df_results = run_experiments(train_loader, val_loader, test_loader)
