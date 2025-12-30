#!/bin/bash

# kích hoạt conda env
OUTPUT = $(conda run -n torch-gpu python demand_forecasting/test_dlinear.py)

# lấy cái output của lệnh trên
echo "WAPE: $OUTPUT"
