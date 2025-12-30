### Cài đặt Backend (FastAPI)
```bash
cd backend
python3.11 -m venv venv
source venv/bin/activate
# hoặc venv\Scripts\activate trên Windows
pip install -r requirements.txt
```
### Cài đặt Frontend (React)
```bash
cd frontend
npm install
```

### Chạy Backend
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
### Chạy Frontend
```bash
cd frontend
npm start
```