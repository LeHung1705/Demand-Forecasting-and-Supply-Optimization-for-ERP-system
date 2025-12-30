#!/bin/bash

set -e

echo "===== Start DLinear Training ====="

echo "[1/4] Imputed + Decoder"
python demand_forecasting/exp/exp_dlinear.py

echo "[2/4] Imputed + No Decoder"
python demand_forecasting/exp/exp_dlinear.py --no_decoder

echo "[3/4] Original + Decoder"
python demand_forecasting/exp/exp_dlinear.py --data_type original

echo "[4/4] Original + No Decoder"
python demand_forecasting/exp/exp_dlinear.py --data_type original --no_decoder

echo "===== All training jobs finished ====="
