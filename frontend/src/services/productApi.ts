// src/services/productApi.ts
const BASE_URL = 'http://localhost:8000/api/v1/products';

// 1. Lấy danh sách
export async function getProducts(page = 1, pageSize = 100) {
  const res = await fetch(`${BASE_URL}?page=${page}&page_size=${pageSize}`);
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
  if (!res.ok) throw new Error('Create failed');
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