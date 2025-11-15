import argparse
import os
import torch
from torch import nn
from tqdm import tqdm
import json

from data_utils.get_loader import get_loader
from models._models import (
    SimpleAverageNet,
    ExponentialSmoothingNet,
    SimpleMovingAverageNet,
    arima_forecast
)


def get_model(name):
    """Factory function để tạo baseline model"""
    name = name.lower()
    if name == "odoo_basic":
        return SimpleAverageNet()
    elif name == "odoo_sota":
        return ExponentialSmoothingNet()
    elif name == "sap_basic":
        return SimpleMovingAverageNet(window_size=3)
    elif name == "arima":
        return "arima"  # Special marker
    else:
        raise ValueError(f"❌ Unknown baseline model: {name}. Use: odoo_basic, sap_basic, arima")


def compute_metrics(pred, target):
    """Tính các metrics đánh giá"""
    pred = pred.reshape(-1)
    target = target.reshape(-1)
    
    mse = torch.mean((pred - target) ** 2)
    mae = torch.mean(torch.abs(pred - target))
    rmse = torch.sqrt(mse)
    
    epsilon = 1e-8
    mape = torch.mean(torch.abs((target - pred) / (target + epsilon))) * 100
    
    return {
        'mse': mse.item(),
        'mae': mae.item(),
        'rmse': rmse.item(),
        'mape': mape.item()
    }


def evaluate_neural_model(model, dataloader, criterion, device, desc="Eval"):
    """Evaluate neural network model"""
    model.eval()
    total_loss = 0
    all_metrics = {'mse': 0, 'mae': 0, 'rmse': 0, 'mape': 0}
    
    with torch.no_grad():
        pbar = tqdm(dataloader, desc=desc, leave=False)
        for x, y in pbar:
            x = x.to(device).float()
            y = y.to(device).float()
            
            # Forward
            pred = model(x)
            
            # Handle shape
            if pred.dim() == 2 and pred.shape[1] == 1:
                pred = pred.unsqueeze(-1)
            
            if y.dim() == 1:
                y = y.unsqueeze(1).unsqueeze(1)
            elif y.dim() == 2:
                y = y.unsqueeze(1)
            
            # Compute loss
            loss = criterion(pred, y)
            
            # Metrics
            total_loss += loss.item()
            batch_metrics = compute_metrics(pred, y)
            for k, v in batch_metrics.items():
                all_metrics[k] += v
            
            pbar.set_postfix({
                'loss': f"{loss.item():.4f}",
                'mae': f"{batch_metrics['mae']:.2f}"
            })
    
    # Average
    num_batches = len(dataloader)
    avg_loss = total_loss / num_batches
    for k in all_metrics:
        all_metrics[k] /= num_batches
    
    return avg_loss, all_metrics


def evaluate_arima(dataloader, criterion, device, arima_params, desc="ARIMA"):
    """Evaluate ARIMA model"""
    total_loss = 0
    all_metrics = {'mse': 0, 'mae': 0, 'rmse': 0, 'mape': 0}
    
    p, d, q = arima_params
    pbar = tqdm(dataloader, desc=desc, leave=False)
    
    for x, y in pbar:
        x = x.to(device).float()
        y = y.to(device).float()
        
        # ARIMA expects (batch, seq_len)
        x_squeezed = x.squeeze(-1)
        
        # Forecast
        pred = arima_forecast(x_squeezed, p=p, d=d, q=q, steps=1)
        
        # Handle shape
        if pred.dim() == 1:
            pred = pred.unsqueeze(1).unsqueeze(1)
        elif pred.dim() == 2:
            pred = pred.unsqueeze(1)
        
        if y.dim() == 1:
            y = y.unsqueeze(1).unsqueeze(1)
        elif y.dim() == 2:
            y = y.unsqueeze(1)
        
        # Compute loss
        loss = criterion(pred, y)
        
        # Metrics
        total_loss += loss.item()
        batch_metrics = compute_metrics(pred, y)
        for k, v in batch_metrics.items():
            all_metrics[k] += v
        
        pbar.set_postfix({
            'loss': f"{loss.item():.4f}",
            'mae': f"{batch_metrics['mae']:.2f}"
        })
    
    # Average
    num_batches = len(dataloader)
    avg_loss = total_loss / num_batches
    for k in all_metrics:
        all_metrics[k] /= num_batches
    
    return avg_loss, all_metrics


def main():
    parser = argparse.ArgumentParser(description="Evaluate Baseline Forecasting Models")
    parser.add_argument("--batch_size", type=int, default=128)
    parser.add_argument("--model", type=str, required=True,
                        help="Model: odoo_basic, sap_basic, arima")
    parser.add_argument("--checkpoint_dir", type=str, default="checkpoints")
    parser.add_argument("--arima_p", type=int, default=1, help="ARIMA p parameter")
    parser.add_argument("--arima_d", type=int, default=1, help="ARIMA d parameter")
    parser.add_argument("--arima_q", type=int, default=0, help="ARIMA q parameter")
    args = parser.parse_args()

    # Setup
    os.makedirs(args.checkpoint_dir, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    print("=" * 70)
    print(f"Evaluating Baseline Model")
    print("=" * 70)
    print(f"Device     : {device}")
    print(f"Model      : {args.model}")
    print(f"Batch size : {args.batch_size}")
    if args.model == "arima":
        print(f"ARIMA order: ({args.arima_p}, {args.arima_d}, {args.arima_q})")
    print("=" * 70)

    # Load data
    print("\n📦 Loading data...")
    train_loader, val_loader, test_loader = get_loader(batch_size=args.batch_size)
    print(f"Train batches: {len(train_loader)}")
    print(f"Val batches  : {len(val_loader)}")
    print(f"Test batches : {len(test_loader)}")

    # Model
    print(f"\nBuilding model: {args.model}")
    model = get_model(args.model)
    
    is_arima = isinstance(model, str) and model == "arima"
    
    if is_arima:
        print(f"Model: ARIMA({args.arima_p}, {args.arima_d}, {args.arima_q})")
        total_params = 0
        trainable_params = 0
    else:
        model = model.to(device)
        total_params = sum(p.numel() for p in model.parameters())
        trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        print(f"Total parameters    : {total_params:,}")
        print(f"Trainable parameters: {trainable_params:,}")
    
    criterion = nn.MSELoss()

    # Evaluate
    print("\n" + "=" * 70)
    print("📈 Evaluation Start")
    print("=" * 70)
    
    arima_params = (args.arima_p, args.arima_d, args.arima_q)
    
    # Train set
    print("\n📊 Evaluating on Train Set...")
    if is_arima:
        train_loss, train_metrics = evaluate_arima(
            train_loader, criterion, device, arima_params, desc="Train (ARIMA)"
        )
    else:
        train_loss, train_metrics = evaluate_neural_model(
            model, train_loader, criterion, device, desc="Train"
        )
    
    print(f"Train Loss: {train_loss:.6f} | MAE: {train_metrics['mae']:.2f} | MAPE: {train_metrics['mape']:.2f}%")
    
    # Val set
    print("\n📊 Evaluating on Val Set...")
    if is_arima:
        val_loss, val_metrics = evaluate_arima(
            val_loader, criterion, device, arima_params, desc="Val (ARIMA)"
        )
    else:
        val_loss, val_metrics = evaluate_neural_model(
            model, val_loader, criterion, device, desc="Val"
        )
    
    print(f"Val Loss  : {val_loss:.6f} | MAE: {val_metrics['mae']:.2f} | MAPE: {val_metrics['mape']:.2f}%")
    
    # Test set
    print("\nEvaluating on Test Set...")
    if is_arima:
        test_loss, test_metrics = evaluate_arima(
            test_loader, criterion, device, arima_params, desc="Test (ARIMA)"
        )
    else:
        test_loss, test_metrics = evaluate_neural_model(
            model, test_loader, criterion, device, desc="Test"
        )
    
    print(f"\n📈 Final Results ({args.model}):")
    print("-" * 70)
    print(f"Test Loss: {test_loss:.6f}")
    print(f"Test MAE : {test_metrics['mae']:.2f}")
    print(f"Test RMSE: {test_metrics['rmse']:.2f}")
    print(f"Test MAPE: {test_metrics['mape']:.2f}%")
    
    # Save results
    results = {
        'model': args.model,
        'best_val_loss': val_loss,
        'best_val_metrics': val_metrics,
        'test_loss': test_loss,
        'test_metrics': test_metrics,
        'total_params': total_params,
        'trainable_params': trainable_params
    }
    
    if is_arima:
        results['arima_params'] = arima_params
    
    with open(f"{args.checkpoint_dir}/{args.model}_results.json", 'w') as f:
        json.dump(results, f, indent=2)
    
    # Save dummy checkpoint for compatibility
    if is_arima:
        torch.save({
            'arima_params': arima_params,
            'val_loss': val_loss,
            'val_metrics': val_metrics
        }, f"{args.checkpoint_dir}/{args.model}_best.pt")
    else:
        torch.save({
            'model_state_dict': model.state_dict(),
            'val_loss': val_loss,
            'val_metrics': val_metrics
        }, f"{args.checkpoint_dir}/{args.model}_best.pt")
    
    print(f"\n✅ Results saved to {args.checkpoint_dir}/{args.model}_results.json")
    print("=" * 70)


if __name__ == "__main__":
    main()