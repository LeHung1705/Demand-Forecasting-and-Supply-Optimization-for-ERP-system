import pandas as pd
import numpy as np
import os
import warnings
warnings.filterwarnings('ignore')

def mimic_missing(patch_ts, p=0.3, max_missing_patch=7, min_missing_patch=3):
    patch_len = patch_ts.shape[-1]
    patch_num = patch_ts.shape[1]
    batch_size = patch_ts.shape[0]
    patch_time = np.arange(patch_len)[None,None,:] 
    patch_missing_cnt = np.isnan(patch_ts).sum(axis=-1, keepdims=True)
    non_missing_idx = patch_missing_cnt==0
    
    non_missing_cumsum = np.zeros_like(non_missing_idx.astype(int))
    sum_vec = np.zeros_like(non_missing_idx[:,0].astype(int))
    conti_idx = np.zeros_like(non_missing_idx)
    
    for i in range(patch_num):
        sum_vec = np.where(non_missing_idx[:,i], sum_vec, 0)
        sum_vec = sum_vec + non_missing_idx[:,i].astype(int)
        non_missing_cumsum[:,i] = sum_vec.copy()
        if i>max_missing_patch:
            conti_len = np.random.randint(low=min_missing_patch, high=max_missing_patch+1, size=sum_vec.shape)
            conti_len = np.where((conti_len < sum_vec) & (np.random.rand(*sum_vec.shape)<p/10), conti_len, 0)
            conti_tmp = np.arange(batch_size * max_missing_patch).reshape(batch_size, max_missing_patch, 1)
            conti_tmp = max_missing_patch - (conti_tmp - conti_tmp[:,0:1])
            conti_tmp = (conti_tmp <= conti_len[:,None]) & (conti_tmp > 1)
            conti_idx[:,i-max_missing_patch+1:i+1] = conti_idx[:,i-max_missing_patch+1:i+1] | conti_tmp
            
    intra_rand_idx = (np.random.rand(*patch_missing_cnt.shape) < p) & non_missing_idx
    patch_missing_start_time = np.random.randint(low=0, high=int(patch_len*(1-p)), size=patch_missing_cnt.shape)
    patch_missing_end_time = patch_len - patch_missing_start_time
    intra_missing_idx_front = patch_time>=patch_missing_start_time
    intra_missing_idx_backend = patch_time<=patch_missing_end_time
    shape = list(intra_missing_idx_front.shape)
    shape[-1] = 1
    intra_missing_idx = np.where(np.random.rand(*shape)<=0.5, intra_missing_idx_front, intra_missing_idx_backend)
    intra_idx = intra_rand_idx & intra_missing_idx

    sample_idx = intra_idx | conti_idx

    patch_ts_missing = np.where(sample_idx, np.nan, patch_ts)
    valid_idx = ~np.isnan(patch_ts)&np.isnan(patch_ts_missing)
    return patch_ts_missing, valid_idx

def main():
    print("Processing data from data/original_data.csv...")
    try:
        # Load local data instead of HuggingFace
        data = pd.read_csv('data/original_data.csv')
        data['dt'] = pd.to_datetime(data['dt'])
        data = data.sort_values(by=['store_id', 'product_id', 'dt'])
        
        # Parse list strings if necessary (handling format from csv)
        if isinstance(data['hours_sale'].iloc[0], str):
             data['hours_sale'] = data['hours_sale'].apply(lambda x: eval(x) if x.startswith('[') else x)
        if isinstance(data['hours_stock_status'].iloc[0], str):
             data['hours_stock_status'] = data['hours_stock_status'].apply(lambda x: eval(x) if x.startswith('[') else x)

    except Exception as e:
        print(f"Error loading local data: {e}")
        return

    horizon = 90
    series_num = data.shape[0] // horizon
    
    hours_sale = np.array(data['hours_sale'].tolist())
    hours_stock_status = np.array(data['hours_stock_status'].tolist())

    # Reshape and process
    hours_sale_origin = hours_sale.reshape(series_num, horizon, -1)[..., 6:22]
    hours_stock_status = hours_stock_status.reshape(series_num, horizon, -1)[..., 6:22]
    
    hours_sale = np.where(hours_stock_status == 1, np.nan, hours_sale_origin)
    
    covariate = data[['discount', 'holiday_flag', 'precpt', 'avg_temperature']].values.reshape(series_num, horizon, -1)
    covariate = covariate/(covariate.max(axis=1, keepdims=True)+0.1)

    hours_sale, valid_idx = mimic_missing(hours_sale, p=0.3, max_missing_patch=7, min_missing_patch=3)
    
    covariate = np.expand_dims(covariate, axis=2)
    covariate = np.broadcast_to(covariate, (series_num, horizon, hours_sale.shape[2], covariate.shape[-1]))
    hours_sale = np.expand_dims(hours_sale, axis=-1)
    hour_encoding = np.broadcast_to(np.arange(16)[None,None,:,None]/15, (series_num, horizon, 16, 1))
    
    train_set = np.concatenate([hours_sale, hour_encoding, covariate], axis=-1)
    train_set = train_set.reshape(series_num, horizon*hours_sale.shape[2], -1)
    valid_idx = valid_idx[..., None].reshape(series_num, horizon*hours_sale.shape[2], 1)

    output_path = 'data/processed_data.npz'
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    dataset = {
        'train_set': train_set,
        'valid_idx': valid_idx,
        'hours_sale_origin': hours_sale_origin,
    }
    np.savez_compressed(output_path, **dataset)
    print(f"Data saved to {output_path}")

if __name__ == '__main__':
    main()
