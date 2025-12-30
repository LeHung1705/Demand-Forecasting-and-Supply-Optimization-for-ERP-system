import torch
import numpy as np
import matplotlib.pyplot as plt
import sys
sys.path.append('/home/guest/DemandForecasting')

# Choose model: 'timesnet', 'timesnet_v1', or 'dlinear'
MODEL_TYPE = 'timesnet'  # Change this to 'timesnet', 'timesnet_v1', or 'dlinear'

if MODEL_TYPE == 'timesnet':
    from model.timesnet import Model
    
    class Config:
        def __init__(self):
            self.seq_len = 1440
            self.pred_len = 0
            self.label_len = 0
            self.task_name = 'imputation'
            self.enc_in = 6
            self.c_out = 6
            self.d_model = 64
            self.d_ff = 32
            self.num_kernels = 5
            self.top_k = 7
            self.e_layers = 2
            self.embed = 'timeF'
            self.freq = 'h'
            self.dropout = 0.
    
    checkpoint_path = 'latent_demand_recovery/checkpoints/timesnet_best.pth'

elif MODEL_TYPE == 'timesnet_v1':
    from model.timesnet import Model
    
    class Config:
        def __init__(self):
            self.seq_len = 1440
            self.pred_len = 0
            self.label_len = 0
            self.task_name = 'imputation'
            self.enc_in = 6
            self.c_out = 6
            self.d_model = 64
            self.d_ff = 128
            self.num_kernels = 5
            self.top_k = 7
            self.e_layers = 2
            self.embed = 'timeF'
            self.freq = 'h'
            self.dropout = 0.
    
    checkpoint_path = 'latent_demand_recovery/checkpoints/timesnet_v1_best.pth'
    
elif MODEL_TYPE == 'dlinear':
    from model.dlinear import Model
    
    class Config:
        def __init__(self):
            self.seq_len = 1440
            self.pred_len = 1440
            self.enc_in = 6
            self.individual = True
    
    checkpoint_path = 'latent_demand_recovery/checkpoints/dlinear_best.pth'
    
else:
    raise ValueError(f"Unknown model type: {MODEL_TYPE}. Choose 'timesnet', 'timesnet_v1', or 'dlinear'")

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model = Model(Config()).to(device)
model.load_state_dict(torch.load(checkpoint_path, map_location=device))
model.eval()

print(f"Using model: {MODEL_TYPE.upper()}")
print(f"Checkpoint: {checkpoint_path}")

raw_data = np.load('data/processed_data.npz')
train_set = raw_data['train_set']
valid_idx = raw_data['valid_idx']
hours_sale_origin = raw_data['hours_sale_origin']
del raw_data

train_set_filled = np.nan_to_num(train_set.copy(), nan=0.0)
mask = np.ones_like(train_set, dtype=np.float32)
mask[:, :, 0] = (~valid_idx[:, :, 0]).astype(np.float32)
missing_mask = valid_idx[:, :, 0]

print(f"Imputing {len(train_set)} sequences...")
imputed_all = []
batch_size = 128

with torch.no_grad():
    for i in range(0, len(train_set), batch_size):
        batch = train_set_filled[i:i+batch_size]
        batch_mask = mask[i:i+batch_size]
        
        x_enc = torch.FloatTensor(batch).to(device)
        batch_mask_t = torch.FloatTensor(batch_mask).to(device)
        
        if MODEL_TYPE in ['timesnet', 'timesnet_v1']:
            output = model(x_enc, None, x_enc.clone(), None, batch_mask_t)
        else:  # dlinear
            output = model.imputation(x_enc)
        
        imputed_all.append(output.cpu().numpy())

imputed_data = np.concatenate(imputed_all, axis=0)
del imputed_all, train_set_filled, mask

# Model predictions for all positions
model_predictions_flat = imputed_data[:, :, 0]
# Clip to ensure non-negative sales
model_predictions_flat = np.clip(model_predictions_flat, 0.0, None)
del imputed_data

hours_sale_origin_flat = hours_sale_origin.reshape(len(hours_sale_origin), -1)

# Get raw data (with missing) for comparison
hours_sale_raw_flat = train_set[:, :, 0]
del train_set

# IMPORTANT: Combine observed (from raw) + imputed (from model)
# Keep observed values, only replace missing positions
hours_sale_imputed_flat = np.nan_to_num(hours_sale_raw_flat.copy(), nan=0.0)
hours_sale_imputed_flat[missing_mask] = model_predictions_flat[missing_mask]

missing_positions = missing_mask
original_values = hours_sale_origin_flat[missing_positions]
imputed_values = hours_sale_imputed_flat[missing_positions]

mae = np.abs(original_values - imputed_values).mean()
rmse = np.sqrt(((original_values - imputed_values) ** 2).mean())

print(f"\nOverall Metrics (All Missing Positions):")
print(f"  MAE: {mae:.4f}")
print(f"  RMSE: {rmse:.4f}")

# Calculate Decoupling Score for RAW data (before imputation)
print(f"\n{'='*60}")
print(f"DECOUPLING SCORE COMPARISON")
print(f"{'='*60}")

stockout_ratio = missing_mask.astype(float)
series_num = len(hours_sale_origin)

# 1. Raw data (with NaN replaced by 0)
raw_data_filled = np.nan_to_num(hours_sale_raw_flat, nan=0.0)
correlations_raw = []
weights_raw = []

for i in range(series_num):
    sr_i = stockout_ratio[i]
    d_i = raw_data_filled[i]
    
    if sr_i.std() > 0 and d_i.std() > 0:
        corr = np.corrcoef(sr_i, d_i)[0, 1]
        if not np.isnan(corr):
            correlations_raw.append(corr)
            mean_sales = hours_sale_origin_flat[i].mean()
            weights_raw.append(mean_sales)

correlations_raw = np.array(correlations_raw)
weights_raw = np.array(weights_raw)
weights_raw = weights_raw / weights_raw.sum()

decoupling_score_raw = np.sum(weights_raw * correlations_raw)

print(f"\n1. Raw Data (Before Imputation):")
print(f"   Decoupling Score (ρ_DS): {decoupling_score_raw:.4f}")

# 2. Imputed data
correlations = []
weights = []

for i in range(series_num):
    sr_i = stockout_ratio[i]
    d_i = hours_sale_imputed_flat[i]
    
    if sr_i.std() > 0 and d_i.std() > 0:
        corr = np.corrcoef(sr_i, d_i)[0, 1]
        if not np.isnan(corr):
            correlations.append(corr)
            mean_sales = hours_sale_origin_flat[i].mean()
            weights.append(mean_sales)

correlations = np.array(correlations)
weights = np.array(weights)
weights = weights / weights.sum()

decoupling_score = np.sum(weights * correlations)

print(f"\n2. Imputed Data (After {MODEL_TYPE.upper()}):")
print(f"   Decoupling Score (ρ_DS): {decoupling_score:.4f}")

print(f"\n3. Improvement:")
print(f"   Δ = {decoupling_score_raw:.4f} → {decoupling_score:.4f}")
print(f"   Change: {abs(decoupling_score - decoupling_score_raw):.4f}")
print(f"{'='*60}")

print(f"\nTotal missing rate: {missing_positions.sum()}/{missing_positions.size} ({missing_positions.sum()/missing_positions.size*100:.1f}%)")

# Visualization: Single series with 1000 points
sample_series_idx = np.random.randint(0, series_num)
n_points = min(1000, hours_sale_origin_flat.shape[1])

sample_original = hours_sale_origin_flat[sample_series_idx][:n_points]
sample_imputed = hours_sale_imputed_flat[sample_series_idx][:n_points]
sample_missing = missing_mask[sample_series_idx][:n_points]

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10))

# Plot 1: Original sales with missing marked
observed_mask = ~sample_missing
time_steps = np.arange(n_points)

ax1.plot(time_steps, sample_original, 'b-', alpha=0.5, linewidth=1, label='Sales Trend')
ax1.scatter(time_steps[sample_missing], sample_original[sample_missing],
           c='red', s=50, alpha=0.8, label=f'Missing Positions ({sample_missing.sum()})', marker='x', linewidths=2)
ax1.set_ylabel('Sales', fontsize=12)
ax1.set_title(f'Original Sales with Missing Positions (Series {sample_series_idx}, {n_points} points)', 
             fontsize=14, fontweight='bold')
ax1.legend(fontsize=11, loc='upper right')
ax1.grid(True, alpha=0.3)

# Plot 2: Imputed sales with imputed values marked
ax2.plot(time_steps, sample_imputed, 'g-', alpha=0.5, linewidth=1, label='Sales Trend')
ax2.scatter(time_steps[sample_missing], sample_imputed[sample_missing],
           c='orange', s=50, alpha=0.8, label=f'Imputed Values ({sample_missing.sum()})', marker='o', 
           edgecolors='red', linewidths=1.5)
ax2.set_xlabel('Time Steps (Hours)', fontsize=12)
ax2.set_ylabel('Sales', fontsize=12)
ax2.set_title(f'Sales After Imputation (Series {sample_series_idx})', 
             fontsize=14, fontweight='bold')
ax2.legend(fontsize=11, loc='upper right')
ax2.grid(True, alpha=0.3)

plt.suptitle(f'Imputation Visualization ({MODEL_TYPE.upper()})\nMAE={mae:.4f}, RMSE={rmse:.4f}, ρ_DS={decoupling_score:.4f}\nMissing Rate: {sample_missing.sum()}/{n_points} ({sample_missing.sum()/n_points*100:.1f}%)', 
            fontsize=14, fontweight='bold', y=0.995)

plt.tight_layout()
plt.savefig(f'latent_demand_recovery/imputation_visualization_{MODEL_TYPE}.png', dpi=300, bbox_inches='tight')
print(f"\nVisualization saved to: latent_demand_recovery/imputation_visualization_{MODEL_TYPE}.png")
