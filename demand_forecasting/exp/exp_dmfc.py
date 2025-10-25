import argparse
import torch
from torch import nn, optim
from data_utils.get_loader import get_loader
from models.odoo_basic import SimpleAverageNet
from models.odoo_sota import ExponentialSmoothingNet
from models.sap_basic import SimpleMovingAverageNet
from models.sap_sota import LSTMForecastNet


def get_model(name):
    name = name.lower()
    if name == "odoo_basic":
        return SimpleAverageNet()
    elif name == "odoo_sota":
        return ExponentialSmoothingNet()
    elif name == "sap_basic":
        return SimpleMovingAverageNet()
    elif name == "sap_sota":
        return LSTMForecastNet()
    else:
        raise ValueError(f"❌ Unknown model name: {name}")


def train_one_epoch(model, dataloader, optimizer, criterion, device):
    model.train()
    total_loss = 0
    for x, y in dataloader:
        x, y = x.to(device).float(), y.to(device).float().unsqueeze(1)
        optimizer.zero_grad()
        pred = model(x)
        loss = criterion(pred, y)
        if optimizer is not None:
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
        total_loss += loss.item()
    return total_loss / len(dataloader)


def evaluate(model, dataloader, criterion, device):
    model.eval()
    total_loss = 0
    with torch.no_grad():
        for x, y in dataloader:
            x, y = x.to(device).float(), y.to(device).float().unsqueeze(1)
            pred = model(x)
            loss = criterion(pred, y)
            total_loss += loss.item()
    return total_loss / len(dataloader)


def main():
    parser = argparse.ArgumentParser(description="Demand Forecasting Experiment")
    parser.add_argument("--batch_size", type=int, default=128, help="Batch size")
    parser.add_argument("--model", type=str, required=True, help="Model name: odoo_basic, odoo_sota, sap_basic, sap_sota")
    args = parser.parse_args()

    # --- Setup ---
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    print(f"Model: {args.model} | Batch size: {args.batch_size}")

    # --- Load data ---
    train_loader, val_loader, test_loader = get_loader(batch_size=args.batch_size)

    # --- Model ---
    model = get_model(args.model).to(device)
    criterion = nn.MSELoss()

    if any(p.requires_grad for p in model.parameters()):
        optimizer = optim.Adam(model.parameters(), lr=1e-3)
    else:
        optimizer = None
        print("⚠️ Model không có tham số học được — bỏ qua optimizer.")

    # --- Training loop ---
    best_val_loss = float("inf")
    for epoch in range(10):
        train_loss = train_one_epoch(model, train_loader, optimizer, criterion, device)
        val_loss = evaluate(model, val_loader, criterion, device)

        print(f"[Epoch {epoch:02d}] Train Loss: {train_loss:.6f} | Val Loss: {val_loss:.6f}")

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            torch.save(model.state_dict(), f"checkpoints/{args.model}_best.pt")

    # --- Test ---
    model.load_state_dict(torch.load(f"checkpoints/{args.model}_best.pt"))
    test_loss = evaluate(model, test_loader, criterion, device)
    print(f"✅ Test Loss ({args.model}): {test_loss:.6f}")


if __name__ == "__main__":
    main()
