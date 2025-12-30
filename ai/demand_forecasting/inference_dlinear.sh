#!/bin/bash

# Script để chạy test demand forecasting

# Activate conda environment
source ~/miniconda3/etc/profile.d/conda.sh
conda activate torch-gpu || exit 1

START_DAY=$1
MONTH=$2
YEAR=$3
DECODER_FLAG=$4   # có thể rỗng hoặc --no_decoder

if [ "$#" -lt 3 ]; then
  echo "Usage: $0 <start_day> <month> <year> [--no_decoder]"
  exit 1
fi

python /home/quang_ai/Demand-Forecasting-and-Supply-Optimization-for-ERP-system/ai/demand_forecasting/inference_dlinear.py \
  --start_day "$START_DAY" \
  --month "$MONTH" \
  --year "$YEAR" \
  $DECODER_FLAG
