# Frontend - Demand Forecasting Dashboard

React application cho hệ thống dự báo nhu cầu và tối ưu hóa cung ứng.

## 🚀 Cài đặt

```bash
# Cài đặt dependencies
npm install

# Copy file .env
cp .env.example .env

# Chỉnh sửa .env với backend API URL
```

## 💻 Development

```bash
# Chạy development server
npm start

# Ứng dụng sẽ mở tại http://localhost:3000
```

## 🏗️ Build

```bash
# Build cho production
npm run build

# Serve production build
npx serve -s build
```

## 📁 Cấu trúc thư mục

```
src/
├── components/          # React components
│   ├── common/         # Reusable components
│   ├── charts/         # Chart components
│   ├── layout/         # Layout components (Header, Sidebar, Footer)
│   └── features/       # Feature-specific components
├── pages/              # Page components
├── services/           # API services
├── hooks/              # Custom React hooks
├── context/            # React Context
├── utils/              # Utility functions
└── styles/             # Global styles
```

## 🛠️ Tech Stack

- **React** 18.2.0 - UI Library
- **React Router** - Routing
- **Axios** - HTTP client
- **React Query** - Server state management
- **Zustand** - Client state management
- **Material-UI** - UI components
- **Recharts / Chart.js** - Data visualization
- **React Toastify** - Notifications

## 🔧 Cấu hình

Chỉnh sửa file `.env`:

```env
REACT_APP_API_URL=http://localhost:8000
REACT_APP_API_TIMEOUT=30000
REACT_APP_NAME=Demand Forecasting Dashboard
REACT_APP_VERSION=1.0.0
```

## 📄 Available Scripts

- `npm start` - Run development server
- `npm build` - Build for production
- `npm test` - Run tests
- `npm eject` - Eject from Create React App

## 📝 Features

- ✅ Dashboard với thống kê tổng quan
- ✅ Quản lý sản phẩm
- ✅ Dự báo nhu cầu
- ✅ Phân tích và báo cáo
- ✅ Cài đặt hệ thống
- 🔲 Tích hợp với Backend API
- 🔲 Authentication & Authorization
- 🔲 Real-time updates
- 🔲 Export reports
