import React, { useEffect, useState } from 'react';
import { getProducts, createProduct, updateProduct, deleteProduct } from '../services/productApi';
import './Dashboard.css'; // Tận dụng CSS cũ cho đẹp

const ProductManagement = () => {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(false);
  
  // State phân trang
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const pageSize = 50;
  
  // State cho Form (Modal)
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState(null); // Nếu null là Thêm mới, có ID là Sửa
  
  // Dữ liệu form
  const [formData, setFormData] = useState({
    product_id: '',
    first_category_id: '',
    second_category_id: '',
    third_category_id: '',
    management_group_id: ''
  });

  // 1. Load dữ liệu khi vào trang
  const loadData = async () => {
    setLoading(true);
    try {
      const res = await getProducts(page, pageSize);
      setProducts(res.items || []);
      
      // Tính tổng số trang
      if (res.total) {
        setTotalPages(Math.ceil(res.total / pageSize));
      }
    } catch (err) {
      console.error('Load Error:', err);
      alert('Lỗi tải danh sách sản phẩm');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [page]);

  // 2. Xử lý Xóa
  const handleDelete = async (id) => {
    if (window.confirm(`Bạn chắc chắn muốn xóa sản phẩm ID: ${id}?`)) {
      try {
        await deleteProduct(id);
        alert('Xóa thành công!');
        loadData(); // Tải lại bảng
      } catch (err) {
        alert('Lỗi: Không thể xóa (có thể do ràng buộc dữ liệu Sales)');
      }
    }
  };

  // 3. Xử lý Mở Form
  const openAddForm = () => {
    setEditingId(null);
    setFormData({ product_id: '', first_category_id: '', second_category_id: '', third_category_id: '', management_group_id: '' });
    setShowForm(true);
  };

  const openEditForm = (product) => {
    setEditingId(product.product_id);
    setFormData({
      product_id: product.product_id,
      first_category_id: product.first_category_id || '',
      second_category_id: product.second_category_id || '',
      third_category_id: product.third_category_id || '',
      management_group_id: product.management_group_id || '',
    });
    setShowForm(true);
  };

  // 4. Xử lý Lưu (Thêm hoặc Sửa)
  const handleSave = async (e) => {
    e.preventDefault();
    try {
      // Convert số vì input form trả về string
      const payload = {
        product_id: Number(formData.product_id),
        first_category_id: Number(formData.first_category_id) || 0,
        second_category_id: Number(formData.second_category_id) || 0,
        third_category_id: Number(formData.third_category_id) || 0,
        management_group_id: Number(formData.management_group_id) || 0,
      };

      if (editingId) {
        await updateProduct(editingId, payload);
        alert('Cập nhật thành công!');
      } else {
        await createProduct(payload);
        alert('Tạo mới thành công!');
      }
      setShowForm(false);
      loadData();
    } catch (err) {
      alert('Lỗi lưu dữ liệu: ' + err.message);
    }
  };

  return (
    <div className="dashboard">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h2 className="page-title">Quản Lý Sản Phẩm</h2>
        <button 
          onClick={openAddForm}
          style={{ padding: '10px 20px', background: '#2196f3', color: 'white', border: 'none', borderRadius: 4, cursor: 'pointer' }}
        >
          + Thêm Sản Phẩm
        </button>
      </div>

      {/* --- FORM MODAL (Hiển thị khi showForm = true) --- */}
      {showForm && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.5)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000
        }}>
          <div className="card" style={{ width: 400, padding: 20 }}>
            <h3>{editingId ? 'Cập nhật sản phẩm' : 'Thêm sản phẩm mới'}</h3>
            <form onSubmit={handleSave}>
  {/* 1. PRODUCT ID */}
  <div style={{ marginBottom: 15 }}>
    <label style={{ display: 'block', marginBottom: 5, fontWeight: 'bold' }}>Product ID (Bắt buộc):</label>
    <input 
      type="number" 
      required 
      disabled={!!editingId} 
      value={formData.product_id}
      onChange={e => setFormData({...formData, product_id: e.target.value})}
      style={{ width: '100%', padding: '8px', border: '1px solid #ccc', borderRadius: 4 }}
      placeholder="Ví dụ: 20000"
    />
  </div>

  {/* 2. CATEGORY LEVEL 1 */}
  <div style={{ marginBottom: 15 }}>
    <label style={{ display: 'block', marginBottom: 5 }}>Danh mục cấp 1 (First Category):</label>
    <input 
      type="number" 
      value={formData.first_category_id}
      onChange={e => setFormData({...formData, first_category_id: e.target.value})}
      style={{ width: '100%', padding: '8px', border: '1px solid #ccc', borderRadius: 4 }}
      placeholder="Ví dụ: 1"
    />
  </div>

  {/* 3. CATEGORY LEVEL 2 (MỚI THÊM) */}
  <div style={{ marginBottom: 15 }}>
    <label style={{ display: 'block', marginBottom: 5 }}>Danh mục cấp 2 (Second Category):</label>
    <input 
      type="number" 
      value={formData.second_category_id} // Map vào biến second
      onChange={e => setFormData({...formData, second_category_id: e.target.value})}
      style={{ width: '100%', padding: '8px', border: '1px solid #ccc', borderRadius: 4 }}
      placeholder="Ví dụ: 10"
    />
  </div>

  {/* 4. CATEGORY LEVEL 3 (MỚI THÊM) */}
  <div style={{ marginBottom: 15 }}>
    <label style={{ display: 'block', marginBottom: 5 }}>Danh mục cấp 3 (Third Category):</label>
    <input 
      type="number" 
      value={formData.third_category_id} // Map vào biến third (bạn cần check lại state formData có biến này chưa)
      onChange={e => setFormData({...formData, third_category_id: e.target.value})}
      style={{ width: '100%', padding: '8px', border: '1px solid #ccc', borderRadius: 4 }}
      placeholder="Ví dụ: 100"
    />
  </div>

  {/* 5. GROUP ID */}
  <div style={{ marginBottom: 15 }}>
    <label style={{ display: 'block', marginBottom: 5 }}>Nhóm quản lý (Group ID):</label>
    <input 
      type="number" 
      value={formData.management_group_id}
      onChange={e => setFormData({...formData, management_group_id: e.target.value})}
      style={{ width: '100%', padding: '8px', border: '1px solid #ccc', borderRadius: 4 }}
      placeholder="Ví dụ: 5"
    />
  </div>

  <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 25 }}>
    <button 
      type="button" 
      onClick={() => setShowForm(false)}
      style={{ padding: '8px 16px', cursor: 'pointer', background: '#e0e0e0', border: 'none', borderRadius: 4 }}
    >
      Hủy
    </button>
    <button 
      type="submit" 
      style={{ padding: '8px 16px', background: '#4caf50', color: 'white', border: 'none', borderRadius: 4, cursor: 'pointer' }}
    >
      Lưu
    </button>
  </div>
</form>
          </div>
        </div>
      )}

      {/* --- BẢNG DANH SÁCH --- */}
      <div className="card">
        {loading ? <p>Đang tải...</p> : (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: '#f5f5f5' }}>
                <th style={{ padding: 10, textAlign: 'left' }}>Product ID</th>
                <th style={{ padding: 10, textAlign: 'left' }}>Category</th>
                <th style={{ padding: 10, textAlign: 'left' }}>Group</th>
                <th style={{ padding: 10, textAlign: 'right' }}>Hành động</th>
              </tr>
            </thead>
            <tbody>
              {products.map((p) => (
                <tr key={p.product_id} style={{ borderBottom: '1px solid #eee' }}>
                  <td style={{ padding: 10 }}>{p.product_id}</td>
                  <td style={{ padding: 10 }}>{p.first_category_id}</td>
                  <td style={{ padding: 10 }}>{p.management_group_id}</td>
                  <td style={{ padding: 10, textAlign: 'right' }}>
                    <button 
                      onClick={() => openEditForm(p)}
                      style={{ marginRight: 10, color: 'blue', background: 'none', border: 'none', cursor: 'pointer' }}
                    >
                      Sửa
                    </button>
                    <button 
                      onClick={() => handleDelete(p.product_id)}
                      style={{ color: 'red', background: 'none', border: 'none', cursor: 'pointer' }}
                    >
                      Xóa
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        
        {/* --- PHÂN TRANG --- */}
        {!loading && products.length > 0 && (
          <div style={{ marginTop: 20, display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 15 }}>
            <button 
              disabled={page === 1}
              onClick={() => setPage(p => p - 1)}
              style={{ 
                padding: '8px 16px', 
                cursor: page === 1 ? 'not-allowed' : 'pointer', 
                opacity: page === 1 ? 0.5 : 1,
                background: '#2196f3',
                color: 'white',
                border: 'none',
                borderRadius: 4
              }}
            >
              &lt; Trang trước
            </button>

            <span style={{ fontWeight: 'bold' }}>
              Trang {page} / {totalPages}
            </span>

            <button 
              disabled={page >= totalPages}
              onClick={() => setPage(p => p + 1)}
              style={{ 
                padding: '8px 16px', 
                cursor: page >= totalPages ? 'not-allowed' : 'pointer', 
                opacity: page >= totalPages ? 0.5 : 1,
                background: '#2196f3',
                color: 'white',
                border: 'none',
                borderRadius: 4
              }}
            >
              Trang sau &gt;
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default ProductManagement;