#!/bin/bash

# Train All Models Script
# Usage: bash train_all.sh

echo "======================================================================"
echo "🚀 Training & Evaluating All Forecasting Models"
echo "======================================================================"

# Configuration
BATCH_SIZE=128
EPOCHS_TRAINABLE=50
LR=1e-3

# Create directories
mkdir -p checkpoints
mkdir -p runs

echo ""
echo "======================================================================"
echo "📊 PART 1: BASELINE MODELS (Non-trainable - Evaluation Only)"
echo "======================================================================"

echo ""
echo "----------------------------------------------------------------------"
echo "🧮 ODOO BASIC (Simple Average)"
echo "----------------------------------------------------------------------"
python evaluate_baseline.py \
    --model odoo_basic \
    --batch_size $BATCH_SIZE

echo ""
echo "----------------------------------------------------------------------"
echo "🧮 ODOO OPTIMIZED (Exponential Smoothing)"
echo "----------------------------------------------------------------------"
python evaluate_baseline.py \
    --model odoo_basic \
    --batch_size $BATCH_SIZE

echo ""
echo "----------------------------------------------------------------------"
echo "🏢 SAP BASIC (Simple Moving Average)"
echo "----------------------------------------------------------------------"
python evaluate_baseline.py \
    --model sap_basic \
    --batch_size $BATCH_SIZE

echo ""
echo "----------------------------------------------------------------------"
echo "📊 ARIMA (Statistical Model)"
echo "----------------------------------------------------------------------"
python evaluate_baseline.py \
    --model arima \
    --batch_size $BATCH_SIZE \
    --arima_p 1 \
    --arima_d 1 \
    --arima_q 0

echo ""
echo "======================================================================"
echo "🎯 PART 2: OPTIMIZED MODELS (Trainable - Full Training)"
echo "======================================================================"

echo ""
echo "----------------------------------------------------------------------"
echo "🤖 SAP OPTIMIZED (LSTM)"
echo "----------------------------------------------------------------------"
python train.py \
    --model sap_sota \
    --batch_size $BATCH_SIZE \
    --epochs $EPOCHS_TRAINABLE \
    --lr $LR

echo ""
echo "======================================================================"
echo "✅ All models completed!"
echo "======================================================================"
echo ""
echo "📊 Comparing results..."
python compare_results.py

echo ""
echo "======================================================================"
echo "🎉 Training & Evaluation Complete!"
echo "======================================================================"
echo ""
echo "📁 Files generated:"
echo "  Baseline models (evaluation only):"
echo "    - checkpoints/odoo_basic_best.pt"
echo "    - checkpoints/odoo_basic_results.json"
echo "    - checkpoints/sap_basic_best.pt"
echo "    - checkpoints/sap_basic_results.json"
echo "    - checkpoints/arima_best.pt"
echo "    - checkpoints/arima_results.json"
echo ""
echo "  Trained models:"
echo "    - checkpoints/odoo_sota_best.pt"
echo "    - checkpoints/odoo_sota_results.json"
echo "    - runs/odoo_sota/ (TensorBoard logs)"
echo "    - checkpoints/sap_sota_best.pt"
echo "    - checkpoints/sap_sota_results.json"
echo "    - runs/sap_sota/ (TensorBoard logs)"
echo ""
echo "  Summary:"
echo "    - checkpoints/comparison_results.csv"
echo ""
echo "🔍 To view training progress for optimized models:"
echo "    tensorboard --logdir runs"
echo "======================================================================"