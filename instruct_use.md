### Cài đặt Backend (FastAPI)
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

### Cài đặt Frontend (React)
```bash
cd frontend
# Cài đặt dependencies
npm install
# Tạo file .env từ template
cp .env.example .env
```