// src/services/productApi.ts
const BASE_URL = 'http://localhost:8000/api/v1/products';

// 1. Lấy danh sách
export async function getProducts(
  page = 1,
  pageSize = 100,
  filters?: {
    productId?: string;
    category?: string;
    group?: string;
  }
) {
  const params = new URLSearchParams();
  params.set('page', String(page));
  params.set('page_size', String(pageSize));

  const productId = filters?.productId?.trim();
  const category = filters?.category?.trim();
  const group = filters?.group?.trim();

  if (productId) params.set('product_id', String(Number(productId)));
  if (category) params.set('first_category_id', String(Number(category)));
  if (group) params.set('management_group_id', String(Number(group)));

  const res = await fetch(`${BASE_URL}?${params.toString()}`);
  if (!res.ok) throw new Error('Failed to fetch products');
  return res.json();
}

// 2. Tạo mới
export async function createProduct(data: any) {
  const res = await fetch(BASE_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    let message = `Create failed (${res.status})`;
    try {
      const contentType = res.headers.get('content-type') || '';
      if (contentType.includes('application/json')) {
        const body = await res.json();
        if (typeof body?.detail === 'string') message = body.detail;
        else if (Array.isArray(body?.detail)) message = JSON.stringify(body.detail);
        else message = JSON.stringify(body);
      } else {
        const text = await res.text();
        if (text) message = text;
      }
    } catch {
      // ignore parse errors; keep default message
    }
    throw new Error(message);
  }
  return res.json();
}

// 3. Cập nhật
export async function updateProduct(id: number, data: any) {
  const res = await fetch(`${BASE_URL}/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Update failed');
  return res.json();
}

// 4. Xóa
export async function deleteProduct(id: number) {
  const res = await fetch(`${BASE_URL}/${id}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('Delete failed');
  return true;
}