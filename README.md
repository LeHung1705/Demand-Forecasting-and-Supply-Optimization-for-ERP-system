"# Hệ thống Dự báo Nhu cầu và Tối ưu hóa Cung ứng cho ERP

## 📋 Mô tả dự án

Hệ thống AI/ML tích hợp với ERP để dự báo nhu cầu sản phẩm và tối ưu hóa chuỗi cung ứng. Dự án bao gồm:
- **Demand Forecasting**: Dự báo nhu cầu sản phẩm sử dụng các mô hình deep learning
- **Latent Demand Recovery**: Phát hiện và phục hồi nhu cầu tiềm ẩn
- **Supply Optimization**: Tối ưu hóa kế hoạch cung ứng và quản lý tồn kho

## 🏗️ Kiến trúc dự án

```
.
├── backend/                    # FastAPI Server
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py            # FastAPI application entry
│   │   ├── config.py          # Configuration settings
│   │   ├── database.py        # Database connection
│   │   ├── dependencies.py    # Shared dependencies
│   │   │
│   │   ├── models/            # SQLAlchemy ORM models
│   │   │   ├── __init__.py
│   │   │   ├── product.py
│   │   │   ├── forecast.py
│   │   │   └── supply.py
│   │   │
│   │   ├── schemas/           # Pydantic schemas
│   │   │   ├── __init__.py
│   │   │   ├── product.py
│   │   │   ├── forecast.py
│   │   │   └── supply.py
│   │   │
│   │   ├── routes/            # API endpoints (routers)
│   │   │   ├── __init__.py
│   │   │   ├── products.py
│   │   │   ├── forecasts.py
│   │   │   ├── analytics.py
│   │   │   └── optimization.py
│   │   │
│   │   ├── services/          # Business logic
│   │   │   ├── __init__.py
│   │   │   ├── forecast_service.py
│   │   │   ├── optimization_service.py
│   │   │   └── ml_service.py
│   │   │
│   │   └── utils/             # Helper functions
│   │       ├── __init__.py
│   │       ├── validators.py
│   │       └── helpers.py
│   │
│   ├── tests/                 # Backend tests
│   │   ├── test_api.py
│   │   └── test_services.py
│   │
│   ├── requirements.txt       # Python dependencies
│   ├── .env.example          # Environment variables template
│   └── Dockerfile            # Docker configuration
│
├── frontend/                  # React Application
│   ├── public/
│   │   ├── index.html
│   │   └── favicon.ico
│   │
│   ├── src/
│   │   ├── components/        # Reusable components
│   │   │   ├── common/
│   │   │   │   ├── Button.jsx
│   │   │   │   ├── Input.jsx
│   │   │   │   └── Card.jsx
│   │   │   │
│   │   │   ├── charts/
│   │   │   │   ├── LineChart.jsx
│   │   │   │   ├── BarChart.jsx
│   │   │   │   └── ForecastChart.jsx
│   │   │   │
│   │   │   ├── layout/
│   │   │   │   ├── Header.jsx
│   │   │   │   ├── Sidebar.jsx
│   │   │   │   └── Footer.jsx
│   │   │   │
│   │   │   └── features/
│   │   │       ├── ProductList.jsx
│   │   │       ├── ForecastPanel.jsx
│   │   │       └── OptimizationPanel.jsx
│   │   │
│   │   ├── pages/             # Page components
│   │   │   ├── Dashboard.jsx
│   │   │   ├── Products.jsx
│   │   │   ├── Forecasting.jsx
│   │   │   ├── Analytics.jsx
│   │   │   └── Settings.jsx
│   │   │
│   │   ├── services/          # API services
│   │   │   ├── api.js         # Axios configuration
│   │   │   ├── productService.js
│   │   │   ├── forecastService.js
│   │   │   └── analyticsService.js
│   │   │
│   │   ├── hooks/             # Custom React hooks
│   │   │   ├── useFetch.js
│   │   │   └── useAuth.js
│   │   │
│   │   ├── context/           # React Context
│   │   │   └── AppContext.js
│   │   │
│   │   ├── utils/             # Utility functions
│   │   │   ├── helpers.js
│   │   │   └── constants.js
│   │   │
│   │   ├── styles/            # CSS/SCSS files
│   │   │   ├── global.css
│   │   │   └── variables.css
│   │   │
│   │   ├── App.jsx            # Root component
│   │   └── index.js           # Entry point
│   │
│   ├── package.json           # NPM dependencies
│   ├── .env.example          # Environment variables template
│   └── Dockerfile            # Docker configuration
│
└── model/                     # ML Models
    ├── demand_forecasting/
    │   ├── models/            # Model architectures (ODOO, SAP)
    │   ├── data_utils/        # Data processing
    │   ├── exp/               # Experiments
    │   ├── checkpoints/       # Trained models
    │   ├── main.py           # Training script
    │   └── pyproject.toml    # Dependencies
    │
    └── latent_demand_recovery/
```

## 🚀 Cài đặt

### Yêu cầu hệ thống
- Python >= 3.10, < 3.11
- Node.js >= 16.x
- uv (Python package manager)

### 1. Clone repository

```bash
git clone https://github.com/LeHung1705/Demand-Forecasting-and-Supply-Optimization-for-ERP-system.git
cd Demand-Forecasting-and-Supply-Optimization-for-ERP-system
```

### 2. Cài đặt Model (ML)

```bash
cd model
uv sync
source .venv/bin/activate  # macOS/Linux
# hoặc .venv\Scripts\activate trên Windows
```

### 2. Cài đặt Backend (FastAPI)

```bash
cd backend

# Tạo virtual environment
python -m venv venv
source venv/bin/activate  # macOS/Linux
# hoặc venv\Scripts\activate trên Windows

# Cài đặt dependencies
pip install -r requirements.txt

# Tạo file .env từ template
cp .env.example .env
# Chỉnh sửa .env với thông tin database, API keys, etc.

# Chạy migrations (nếu có)
alembic upgrade head
```

**requirements.txt** nên bao gồm:
```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
pydantic==2.5.0
pydantic-settings==2.1.0
python-dotenv==1.0.0
python-multipart==0.0.6
psycopg2-binary==2.9.9
alembic==1.12.1
pandas==2.1.3
numpy==1.26.2
scikit-learn==1.3.2
torch==2.1.1
```

### 3. Cài đặt Frontend (React)

```bash
cd frontend

# Cài đặt dependencies
npm install

# Tạo file .env từ template
cp .env.example .env
# Chỉnh sửa .env với URL của backend API
```

**package.json** nên bao gồm:
```json
{
  "name": "demand-forecasting-frontend",
  "version": "0.1.0",
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "axios": "^1.6.2",
    "recharts": "^2.10.3",
    "chart.js": "^4.4.0",
    "react-chartjs-2": "^5.2.0",
    "@mui/material": "^5.14.18",
    "@mui/icons-material": "^5.14.18",
    "@emotion/react": "^11.11.1",
    "@emotion/styled": "^11.11.0",
    "react-query": "^3.39.3",
    "zustand": "^4.4.7",
    "date-fns": "^2.30.0"
  },
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build",
    "test": "react-scripts test",
    "eject": "react-scripts eject"
  }
}
```

## 💻 Sử dụng

### Training Model

```bash
cd model/demand_forecasting
# Train tất cả models
bash train_all.sh

# Hoặc train từng model cụ thể
python main.py --model odoo_basic --epochs 100
python main.py --model odoo_sota --epochs 100
```

### Chạy Backend API (FastAPI)

```bash
cd backend

# Development mode với auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Hoặc với hot-reload
uvicorn app.main:app --reload

# Production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

API sẽ chạy tại:
- **API**: http://localhost:8000
- **Swagger Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Chạy Frontend (React)

```bash
cd frontend

# Development mode
npm start
# Ứng dụng sẽ mở tại http://localhost:3000

# Build production
npm run build
# Output trong thư mục build/

# Serve production build
npx serve -s build
```

React app sẽ tự động kết nối với backend API thông qua biến môi trường `REACT_APP_API_URL`

## 📊 Models

### Demand Forecasting Models

1. **ODOO Basic Model** (`odoo_basic.py`)
   - Mô hình baseline cho dữ liệu ODOO ERP
   - Checkpoint: `checkpoints/odoo_basic_best.pt`

2. **ODOO SOTA Model** (`odoo_sota.py`)
   - Mô hình state-of-the-art với kiến trúc nâng cao
   - Checkpoint: `checkpoints/odoo_sota_best.pt`

3. **SAP Basic/SOTA Models**
   - Tương tự cho hệ thống SAP ERP

### Kết quả Training

Kết quả được lưu tại `model/demand_forecasting/checkpoints/*.json`:
- Metrics: MAE, RMSE, MAPE
- Training history
- Hyperparameters

## 🔧 Cấu hình

### Backend (.env)
```env
# Server
APP_NAME=Demand Forecasting API
DEBUG=True
SECRET_KEY=your-secret-key-here

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/demand_forecast_db
# hoặc SQLite cho development
# DATABASE_URL=sqlite:///./app.db

# ML Model
MODEL_PATH=../model/demand_forecasting/checkpoints
MODEL_DEVICE=cpu  # hoặc cuda

# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080

# Redis (optional)
REDIS_URL=redis://localhost:6379/0

# Logging
LOG_LEVEL=INFO
```

### Frontend (.env)
```env
# API Configuration
REACT_APP_API_URL=http://localhost:8000
REACT_APP_API_TIMEOUT=30000

# App Configuration
REACT_APP_NAME=Demand Forecasting Dashboard
REACT_APP_VERSION=1.0.0

# Feature Flags
REACT_APP_ENABLE_ANALYTICS=true
REACT_APP_ENABLE_NOTIFICATIONS=true
```

## 📚 API Documentation

Sau khi chạy backend, truy cập:
- **Swagger UI**: `http://localhost:8000/docs` - Interactive API documentation
- **ReDoc**: `http://localhost:8000/redoc` - Alternative API documentation

### Main Endpoints

#### Products
- `GET /api/v1/products` - Lấy danh sách sản phẩm
- `GET /api/v1/products/{id}` - Lấy chi tiết sản phẩm
- `POST /api/v1/products` - Tạo sản phẩm mới
- `PUT /api/v1/products/{id}` - Cập nhật sản phẩm
- `DELETE /api/v1/products/{id}` - Xóa sản phẩm

#### Forecasting
- `POST /api/v1/forecasts/predict` - Dự báo nhu cầu sản phẩm
  ```json
  {
    "product_id": "string",
    "horizon": 30,
    "model": "odoo_sota"
  }
  ```
- `GET /api/v1/forecasts` - Lấy danh sách dự báo
- `GET /api/v1/forecasts/{id}` - Lấy chi tiết dự báo

#### Analytics
- `GET /api/v1/analytics/dashboard` - Dữ liệu dashboard
- `GET /api/v1/analytics/trends` - Phân tích xu hướng
- `GET /api/v1/analytics/accuracy` - Độ chính xác của model

#### Optimization
- `POST /api/v1/optimize/supply` - Tối ưu hóa cung ứng
  ```json
  {
    "product_ids": ["string"],
    "constraints": {
      "max_inventory": 1000,
      "lead_time": 7
    }
  }
  ```
- `GET /api/v1/optimize/recommendations` - Lấy khuyến nghị

## 🧪 Testing

```bash
# Test backend
cd backend
pytest tests/

# Test models
cd model/demand_forecasting
python exp/model_testing.py
```

## 🛠️ Tech Stack

- **Backend**: FastAPI/Flask, SQLAlchemy, Pydantic
- **Frontend**: React, Axios, Chart.js
- **ML/AI**: PyTorch, Pandas, Scikit-learn, Statsmodels
- **Database**: PostgreSQL/MySQL
- **Deployment**: Docker, Docker Compose

## 📈 Roadmap

- [ ] Hoàn thiện Backend API
- [ ] Phát triển Frontend Dashboard
- [ ] Tích hợp với ODOO/SAP ERP
- [ ] Implement Latent Demand Recovery
- [ ] Thêm Real-time forecasting
- [ ] Deploy lên Cloud (AWS/Azure/GCP)
- [ ] CI/CD Pipeline
- [ ] Unit & Integration Tests