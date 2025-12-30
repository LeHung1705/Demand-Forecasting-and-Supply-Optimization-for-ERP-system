import torch
import torch.nn as nn
from latent_demand_recovery.layers.Autoformer_EncDec import series_decomp

class Model(nn.Module):
    """
    DLinear
    """
    def __init__(self, configs):
        super(Model, self).__init__()
        self.seq_len = configs.seq_len
        self.pred_len = configs.pred_len

        kernel_size = 25
        self.decompsition = series_decomp(kernel_size)
        self.individual = configs.individual
        self.channels = configs.enc_in
        
        self.use_decoder = getattr(configs, 'use_decoder', False)
        if self.use_decoder:
            self.dec_in = getattr(configs, 'dec_in', configs.enc_in - 1)
            self.dec_projection = nn.Linear(self.dec_in, 1)

        if self.individual:
            self.Linear_Seasonal = nn.ModuleList()
            self.Linear_Trend = nn.ModuleList()
            self.Linear_Decoder = nn.ModuleList()
            for i in range(self.channels):
                self.Linear_Seasonal.append(nn.Linear(self.seq_len,self.pred_len))
                self.Linear_Seasonal[i].weight = nn.Parameter((1/self.seq_len)*torch.ones([self.pred_len,self.seq_len]))
                self.Linear_Trend.append(nn.Linear(self.seq_len,self.pred_len))
                self.Linear_Trend[i].weight = nn.Parameter((1/self.seq_len)*torch.ones([self.pred_len,self.seq_len]))
                self.Linear_Decoder.append(nn.Linear(self.seq_len,self.pred_len))
        else:
            self.Linear_Seasonal = nn.Linear(self.seq_len,self.pred_len)
            self.Linear_Trend = nn.Linear(self.seq_len,self.pred_len)
            self.Linear_Decoder = nn.Linear(self.seq_len,self.pred_len)
            self.Linear_Seasonal.weight = nn.Parameter((1/self.seq_len)*torch.ones([self.pred_len,self.seq_len]))
            self.Linear_Trend.weight = nn.Parameter((1/self.seq_len)*torch.ones([self.pred_len,self.seq_len]))

    def forward(self, x, x_dec=None):
        seasonal_init, trend_init = self.decompsition(x)
        seasonal_init, trend_init = seasonal_init.permute(0,2,1), trend_init.permute(0,2,1)
        if self.individual:
            seasonal_output = torch.zeros([seasonal_init.size(0),seasonal_init.size(1),self.pred_len],dtype=seasonal_init.dtype).to(seasonal_init.device)
            trend_output = torch.zeros([trend_init.size(0),trend_init.size(1),self.pred_len],dtype=trend_init.dtype).to(trend_init.device)
            for i in range(self.channels):
                seasonal_output[:,i,:] = self.Linear_Seasonal[i](seasonal_init[:,i,:])
                trend_output[:,i,:] = self.Linear_Trend[i](trend_init[:,i,:])
        else:
            seasonal_output = self.Linear_Seasonal(seasonal_init)
            trend_output = self.Linear_Trend(trend_init)

        pred = seasonal_output + trend_output
        pred = pred.permute(0,2,1)
        
        if self.use_decoder and x_dec is not None:
            dec_out = self.dec_projection(x_dec)
            pred = pred[:, :, -1:] + dec_out
        
        return pred
    
    def imputation(self, x):
        """
        Imputation task: fill in missing values in the input sequence.
        For imputation, we use the decoder to reconstruct the same length sequence.
        
        Args:
            x: [Batch, Input length, Channel] - input with missing values (NaN)
        Returns:
            imputed_x: [Batch, Input length, Channel] - reconstructed values for missing positions
        """
        # x: [Batch, Input length, Channel]
        # For imputation, we only return the reconstructed missing values
        seasonal_init, trend_init = self.decompsition(x)
        seasonal_init, trend_init = seasonal_init.permute(0,2,1), trend_init.permute(0,2,1)
        
        if self.individual:
            seasonal_output = torch.zeros([seasonal_init.size(0),seasonal_init.size(1),self.seq_len],dtype=seasonal_init.dtype).to(seasonal_init.device)
            trend_output = torch.zeros([trend_init.size(0),trend_init.size(1),self.seq_len],dtype=trend_init.dtype).to(trend_init.device)
            for i in range(self.channels):
                seasonal_output[:,i,:] = self.Linear_Decoder[i](seasonal_init[:,i,:])
                trend_output[:,i,:] = self.Linear_Decoder[i](trend_init[:,i,:])
        else:
            seasonal_output = self.Linear_Decoder(seasonal_init)
            trend_output = self.Linear_Decoder(trend_init)
        
        x = seasonal_output + trend_output
        return x.permute(0,2,1) # to [Batch, Output length, Channel]
