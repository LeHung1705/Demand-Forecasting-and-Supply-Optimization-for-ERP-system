from __future__ import annotations

from datetime import date, timedelta
from math import sqrt
from typing import Optional, Dict, Any, List, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import text


def get_sales_date_bounds(
    db: Session,
    store_id: Optional[int] = None,
    product_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Trả về min_dt, max_dt, available_days của bảng sales theo filter.
    """
    sql = """
    SELECT
      MIN(dt) AS min_dt,
      MAX(dt) AS max_dt,
      COUNT(DISTINCT dt) AS available_days
    FROM sales
    WHERE (:store_id IS NULL OR store_id = :store_id)
      AND (:product_id IS NULL OR product_id = :product_id)
    """
    row = db.execute(text(sql), {"store_id": store_id, "product_id": product_id}).mappings().first()

    if not row or row["max_dt"] is None:
        return {"min_dt": None, "max_dt": None, "available_days": 0}

    return {
        "min_dt": str(row["min_dt"]),
        "max_dt": str(row["max_dt"]),
        "available_days": int(row["available_days"] or 0),
    }


def resolve_range_by_max_dt(
    db: Session,
    time_range: str,  # '7d' | '30d' | '90d'
    store_id: Optional[int] = None,
    product_id: Optional[int] = None,
) -> Tuple[Optional[date], Optional[date], Dict[str, Any]]:
    """
    to_date = max_dt theo filter
    from_date = to_date - (7/30/90 - 1) ngày
    Trả thêm meta bounds để frontend biết dataset range.
    """
    bounds = get_sales_date_bounds(db, store_id=store_id, product_id=product_id)

    if bounds["max_dt"] is None:
        return None, None, bounds

    to_date = date.fromisoformat(bounds["max_dt"])

    days = 7
    if time_range == "30d":
        days = 30
    elif time_range == "90d":
        days = 90

    from_date = to_date - timedelta(days=days - 1)  # inclusive

    # clamp nếu from_date < min_dt dataset
    if bounds["min_dt"] is not None:
        min_dt = date.fromisoformat(bounds["min_dt"])
        if from_date < min_dt:
            from_date = min_dt

    return from_date, to_date, bounds


def get_trends_sales_by_day(
    db: Session,
    from_date: date,
    to_date: date,
    store_id: Optional[int] = None,
    product_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    sql = """
    SELECT dt AS k, SUM(sale_amount) AS v
    FROM sales
    WHERE dt BETWEEN :from_d AND :to_d
      AND (:store_id IS NULL OR store_id = :store_id)
      AND (:product_id IS NULL OR product_id = :product_id)
    GROUP BY dt
    ORDER BY dt
    """
    rows = db.execute(
        text(sql),
        {"from_d": from_date, "to_d": to_date, "store_id": store_id, "product_id": product_id},
    ).all()

    points = [{"key": str(r.k), "value": float(r.v or 0)} for r in rows]
    return points


def get_dashboard_data(
    db: Session,
    from_date: date,
    to_date: date,
    store_id: Optional[int] = None,
    product_id: Optional[int] = None,
) -> Dict[str, Any]:
    product_count = db.execute(text("SELECT COUNT(*) FROM product")).scalar() or 0
    store_count = db.execute(text("SELECT COUNT(*) FROM store")).scalar() or 0

    total_sales_sql = """
    SELECT COALESCE(SUM(sale_amount), 0) AS total
    FROM sales
    WHERE dt BETWEEN :from_d AND :to_d
      AND (:store_id IS NULL OR store_id = :store_id)
      AND (:product_id IS NULL OR product_id = :product_id)
    """
    total_sales = db.execute(
        text(total_sales_sql),
        {"from_d": from_date, "to_d": to_date, "store_id": store_id, "product_id": product_id},
    ).scalar() or 0

    trend_points = get_trends_sales_by_day(db, from_date, to_date, store_id=store_id, product_id=product_id)

    return {
        "kpis": {
            "product_count": int(product_count),
            "store_count": int(store_count),
            "total_sales": float(total_sales),
        },
        "trend": {
            "from_date": str(from_date),
            "to_date": str(to_date),
            "store_id": store_id,
            "product_id": product_id,
            "points": trend_points,
        },
    }


# =========================
# CẬP NHẬT LOGIC ACCURACY MỚI (CHUẨN ERP)
# ---------------------------------------------------------

def get_accuracy_data(
    db: Session,
    time_range: str = "30d",
    store_id: Optional[int] = None,
    product_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Tính Accuracy bằng cách so sánh:
    1. Actual Revenue (từ bảng SALES)
    2. Forecast Revenue (từ bảng FORECAST * Giá TB)
    """
    
    # 1. Xác định khung thời gian (30 ngày cuối cùng có dữ liệu)
    # Ta dùng lại hàm resolve_range_by_max_dt để đảm bảo logic thời gian khớp với Dashboard
    from_date, to_date, bounds = resolve_range_by_max_dt(
        db, time_range=time_range, store_id=store_id, product_id=product_id
    )

    if not from_date or not to_date:
        return {"available": False, "message": "Không có dữ liệu sales để so sánh", "metrics": None}

    # 2. Lấy DOANH THU THỰC TẾ (Actual Sales) theo ngày
    # Group by Date để so sánh từng ngày
    sql_actual = """
        SELECT dt, SUM(sale_amount) as val
        FROM sales
        WHERE dt BETWEEN :from_d AND :to_d
          AND (:store_id IS NULL OR store_id = :store_id)
          AND (:product_id IS NULL OR product_id = :product_id)
        GROUP BY dt
    """
    actual_rows = db.execute(text(sql_actual), {
        "from_d": from_date, "to_d": to_date, "store_id": store_id, "product_id": product_id
    }).all()
    
    # Map: '2024-06-25' -> 500000.0
    actual_map = {str(r.dt): float(r.val or 0) for r in actual_rows}

    # 3. Lấy SỐ LƯỢNG DỰ BÁO (Forecast Qty) theo ngày
    # Lưu ý: Bảng forecast của bạn cần có cột forecast_qty
    sql_forecast = """
        SELECT dt, SUM(forecast_qty) as val
        FROM forecast
        WHERE dt BETWEEN :from_d AND :to_d
          AND (:store_id IS NULL OR store_id = :store_id)
          AND (:product_id IS NULL OR product_id = :product_id)
        GROUP BY dt
    """
    try:
        forecast_rows = db.execute(text(sql_forecast), {
            "from_d": from_date, "to_d": to_date, "store_id": store_id, "product_id": product_id
        }).all()
    except Exception as e:
        # Trường hợp chưa tạo bảng forecast hoặc lỗi tên cột
        return {"available": False, "message": f"Lỗi đọc bảng Forecast: {str(e)}", "metrics": None}

    # 4. QUY ĐỔI Forecast Qty -> Forecast Revenue
    # Giả định: Giá trung bình (ASP) = 55,000 VND (Bạn có thể sửa số này)
    AVG_PRICE = 50.0
    forecast_map = {str(r.dt): float(r.val or 0) * AVG_PRICE for r in forecast_rows}

    # 5. Tính toán sai số (MAPE)
    # Chỉ tính trên những ngày CẢ 2 BÊN đều có dữ liệu (Intersection)
    common_dates = set(actual_map.keys()) & set(forecast_map.keys())
    
    if not common_dates:
         return {
            "available": False, 
            "message": "Không tìm thấy ngày trùng khớp giữa Sales và Forecast để chấm điểm.", 
            "metrics": None
        }

    total_ape = 0.0 # Absolute Percentage Error
    count = 0
    total_squared_error = 0.0
    
    y_true_list = []
    y_pred_list = []

    for d in common_dates:
        act = actual_map[d]
        fc = forecast_map[d]
        
        # Bỏ qua ngày doanh thu = 0 để tránh chia cho 0
        if act > 1000: 
            ape = abs(act - fc) / act
            total_ape += ape
            total_squared_error += (act - fc) ** 2
            count += 1
            y_true_list.append(act)
            y_pred_list.append(fc)

    if count == 0:
        return {"available": False, "message": "Dữ liệu quá ít hoặc bằng 0, không thể tính MAPE.", "metrics": None}

    # Tính các chỉ số
    mape = (total_ape / count) * 100
    rmse = sqrt(total_squared_error / count)
    
    # Accuracy Score = 100% - Sai số
    # (Nếu sai số > 100% thì accuracy = 0)
    accuracy_score = max(0, 100 - mape)

    return {
        "available": True,
        "message": f"Đánh giá dựa trên {count} ngày dữ liệu khớp ({from_date} đến {to_date})",
        "baseline": "forecast_table_vs_sales_table",
        "metrics": {
            "mape": round(mape, 2),            # Sai số trung bình (%) - Càng thấp càng tốt
            "accuracy_score": round(accuracy_score, 2), # Độ chính xác (%) - Càng cao càng tốt
            "rmse": round(rmse, 2),            # Sai số căn bậc hai trung bình
            "n": count
        },
        "meta": {
            "from_date": str(from_date),
            "to_date": str(to_date)
        }
    }