import numpy as np
import torch
import sys
sys.path.append('/home/guest/DemandForecasting')
from model.dlinear import Model

class Config:
    def __init__(self):
        # data dimensions
        self.seq_len = 1440
        self.pred_len = 1440
        
        # model architecture
        self.enc_in = 6  # input features: 6
        self.individual = True
        
        # training config
        self.batch_size = 256
        self.lr = 0.001
        self.epochs = 20
        

configs = Config()

# load data
raw_data = np.load('data/processed_data.npz')
train_set = raw_data['train_set']  # (50000, 1440, 6)
valid_idx = raw_data['valid_idx']  # (50000, 1440, 1) - True: missing, False: observed
hours_sale_origin = raw_data['hours_sale_origin']  # (50000, 90, 16) - Ground truth

hours_sale_origin_flat = hours_sale_origin.reshape(len(hours_sale_origin), -1)  # (50000, 1440)

# prepare mask
# Mask logic: 0=missing, 1=observed
# We should only predict positions where:
mask = np.ones((train_set.shape[0], train_set.shape[1], train_set.shape[2]), dtype=np.float32)

# just mask the first feature (hours_sale)
mask[:, :, 0] = (~valid_idx[:, :, 0]).astype(np.float32)

# fill missing values with 0
train_set_filled = np.nan_to_num(train_set.copy(), nan=0.0)


# ============= Training Loop ============= #
# initialize model
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model = Model(configs).to(device)

# optimizer and loss
optimizer = torch.optim.AdamW(model.parameters(), lr=configs.lr, weight_decay=1e-4)
scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.5, patience=3)
criterion = torch.nn.MSELoss()

# training parameters
num_epochs = configs.epochs
batch_size = configs.batch_size
num_samples = len(train_set_filled)

# split train/val
train_size = int(0.8 * num_samples)
indices = np.random.permutation(num_samples)
train_indices = indices[:train_size]
val_indices = indices[train_size:]

print(f"Device: {device}")
print(f"Train samples: {len(train_indices)}, Val samples: {len(val_indices)}")
print(f"Model parameters: {sum(p.numel() for p in model.parameters()):,}")

# Training loop
best_val_loss = float('inf')
patience = 10
patience_counter = 0

for epoch in range(num_epochs):
    model.train()
    train_loss = 0.0
    num_batches = 0
    
    np.random.shuffle(train_indices)
    
    for i in range(0, len(train_indices), batch_size):
        batch_idx = train_indices[i:i+batch_size]
        
        # Prepare batch
        x_enc = torch.FloatTensor(train_set_filled[batch_idx]).to(device)
        target = torch.FloatTensor(hours_sale_origin_flat[batch_idx]).to(device)  # Ground truth from hours_sale_origin
        
        # Forward
        optimizer.zero_grad()
        output = model.imputation(x_enc)
        
        # Loss only on missing positions
        batch_mask = mask[batch_idx]
        missing_mask = (batch_mask[:, :, 0] == 0)
        if missing_mask.sum() > 0:
            # Clip predictions to be non-negative (sales cannot be negative)
            output_clipped = torch.clamp(output[:, :, 0], min=0.0)
            loss = criterion(
                output_clipped[missing_mask],
                target[missing_mask]
            )
            
            # Backward
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            
            train_loss += loss.item()
            num_batches += 1
    
    avg_train_loss = train_loss / num_batches if num_batches > 0 else 0
    
    # Validation
    model.eval()
    val_loss = 0.0
    val_mae = 0.0
    val_batches = 0
    
    with torch.no_grad():
        for i in range(0, len(val_indices), batch_size):
            batch_idx = val_indices[i:i+batch_size]
            
            x_enc = torch.FloatTensor(train_set_filled[batch_idx]).to(device)
            target = torch.FloatTensor(hours_sale_origin_flat[batch_idx]).to(device)
            
            output = model.imputation(x_enc)
            
            batch_mask = mask[batch_idx]
            missing_mask = (batch_mask[:, :, 0] == 0)
            if missing_mask.sum() > 0:
                # Clip predictions to be non-negative
                output_clipped = torch.clamp(output[:, :, 0], min=0.0)
                loss = criterion(
                    output_clipped[missing_mask],  # Only use first feature (hours_sale)
                    target[missing_mask]
                )
                mae = torch.abs(output_clipped[missing_mask] - target[missing_mask]).mean()
                val_loss += loss.item()
                val_mae += mae.item()
                val_batches += 1
    
    avg_val_loss = val_loss / val_batches if val_batches > 0 else 0
    avg_val_mae = val_mae / val_batches if val_batches > 0 else 0
    
    # Learning rate scheduler
    scheduler.step(avg_val_loss)
    
    # Save best model
    if avg_val_loss < best_val_loss:
        best_val_loss = avg_val_loss
        patience_counter = 0
        torch.save(model.state_dict(), 'latent_demand_recovery/checkpoints/dlinear_best.pth')
        print(f"Epoch {epoch+1}/{num_epochs} - Train Loss: {avg_train_loss:.4f}, Val Loss: {avg_val_loss:.4f}, Val MAE: {avg_val_mae:.4f} ✓ (saved)")
    else:
        patience_counter += 1
        print(f"Epoch {epoch+1}/{num_epochs} - Train Loss: {avg_train_loss:.4f}, Val Loss: {avg_val_loss:.4f}, Val MAE: {avg_val_mae:.4f}")
        
        if patience_counter >= patience:
            print(f"Early stopping at epoch {epoch+1}")
            break

print(f"\nTraining completed! Best validation loss: {best_val_loss:.4f}")
print(f"Model saved to: latent_demand_recovery/checkpoints/dlinear_best.pth")
