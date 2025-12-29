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

  // Step 1: Filter states
  const [filterProductId, setFilterProductId] = useState('');
  const [filterCategory, setFilterCategory] = useState('');
  const [filterGroup, setFilterGroup] = useState('');

  // Step 2: Add modal (separate from Edit modal)
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const toggleAddModal = (open) => setIsAddModalOpen(!!open);
  const [addForm, setAddForm] = useState({
    product_id: '',
    first_category_id: '',
    management_group_id: ''
  });
  
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
  const loadData = async (pageToLoad = page, filterOverrides = null) => {
    setLoading(true);
    try {
      const filtersToUse = filterOverrides || {
        productId: filterProductId,
        category: filterCategory,
        group: filterGroup,
      };

      const res = await getProducts(pageToLoad, pageSize, filtersToUse);
      setProducts(res.items || []);
      
      // Tính tổng số trang
      if (res.total) {
        setTotalPages(Math.ceil(res.total / pageSize));
      } else {
        setTotalPages(1);
      }
    } catch (err) {
      console.error('Load Error:', err);
      alert('Lỗi tải danh sách sản phẩm');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData(page);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page]);

  const handleSearch = async () => {
    const productId = String(filterProductId || '').trim();
    const category = String(filterCategory || '').trim();
    const group = String(filterGroup || '').trim();

    // UX-safe: If user enters Product ID, search by ID only.
    // Otherwise, apply category/group filters.
    const filtersToRequest = productId
      ? { productId, category: '', group: '' }
      : { productId: '', category, group };

    // reset to page 1 when searching
    if (page !== 1) {
      setPage(1);
      return;
    }
    await loadData(1, filtersToRequest);
  };

  const handleResetFilters = async () => {
    setFilterProductId('');
    setFilterCategory('');
    setFilterGroup('');

    if (page !== 1) {
      setPage(1);
      return;
    }
    await loadData(1, { productId: '', category: '', group: '' });
  };

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

  // 3. Xử lý Mở Form (Edit)
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

  // 4. Xử lý Lưu (Sửa)
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

      await updateProduct(editingId, payload);
      alert('Cập nhật thành công!');
      setShowForm(false);
      loadData(page);
    } catch (err) {
      alert('Lỗi lưu dữ liệu: ' + err.message);
    }
  };

  const handleAddSave = async (e) => {
    e.preventDefault();
    try {
      const productId = Number(addForm.product_id);
      if (!Number.isFinite(productId) || productId <= 0) {
        alert('Product ID phải là số > 0');
        return;
      }

      const firstCategoryRaw = String(addForm.first_category_id ?? '').trim();
      const groupRaw = String(addForm.management_group_id ?? '').trim();

      const firstCategoryId = firstCategoryRaw === '' ? undefined : Number(firstCategoryRaw);
      const groupId = groupRaw === '' ? undefined : Number(groupRaw);

      if (firstCategoryId !== undefined && !Number.isFinite(firstCategoryId)) {
        alert('Category phải là số');
        return;
      }
      if (groupId !== undefined && !Number.isFinite(groupId)) {
        alert('Group phải là số');
        return;
      }

      const payload = {
        product_id: productId,
        ...(firstCategoryId !== undefined ? { first_category_id: firstCategoryId } : {}),
        ...(groupId !== undefined ? { management_group_id: groupId } : {}),
      };

      await createProduct(payload);
      alert('Tạo mới thành công!');
      toggleAddModal(false);
      setAddForm({ product_id: '', first_category_id: '', management_group_id: '' });

      if (page !== 1) {
        setPage(1);
      } else {
        loadData(1);
      }
    } catch (err) {
      alert('Lỗi lưu dữ liệu: ' + err.message);
    }
  };

  return (
    <div className="dashboard">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h2 className="page-title">Quản Lý Sản Phẩm</h2>
        <button 
          onClick={() => {
            setAddForm({ product_id: '', first_category_id: '', management_group_id: '' });
            toggleAddModal(true);
          }}
          style={{ padding: '10px 20px', background: '#2196f3', color: 'white', border: 'none', borderRadius: 4, cursor: 'pointer' }}
        >
          + Thêm Sản Phẩm
        </button>
      </div>

      {/* Step 1: Filter bar above table */}
      <div
        className="card filter-bar"
        style={{ marginBottom: '20px', padding: '15px', display: 'flex', gap: '10px', alignItems: 'flex-end', flexWrap: 'wrap' }}
      >
        <div>
          <label style={{display: 'block', fontSize: '12px', marginBottom: '5px'}}>Product ID</label>
          <input
            type="number"
            value={filterProductId}
            onChange={(e) => setFilterProductId(e.target.value)}
            placeholder="Lọc theo ID"
            style={{ padding: '8px', border: '1px solid #ddd', borderRadius: '4px', width: 140 }}
          />
        </div>
        <div>
          <label style={{display: 'block', fontSize: '12px', marginBottom: '5px'}}>Category</label>
          <input
            type="text"
            value={filterCategory}
            onChange={(e) => setFilterCategory(e.target.value)}
            placeholder="Lọc Category"
            style={{ padding: '8px', border: '1px solid #ddd', borderRadius: '4px', width: 160 }}
          />
        </div>
        <div>
          <label style={{display: 'block', fontSize: '12px', marginBottom: '5px'}}>Group</label>
          <input
            type="text"
            value={filterGroup}
            onChange={(e) => setFilterGroup(e.target.value)}
            placeholder="Lọc Group"
            style={{ padding: '8px', border: '1px solid #ddd', borderRadius: '4px', width: 160 }}
          />
        </div>
        <button
          onClick={handleSearch}
          style={{ padding: '8px 15px', background: '#2196f3', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
        >
          🔍 Tìm kiếm
        </button>
        <button
          onClick={handleResetFilters}
          style={{ padding: '8px 15px', background: '#f44336', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
        >
          ✕ Xóa lọc
        </button>
      </div>

      {/* Step 2: Add Modal */}
      {isAddModalOpen && (
        <>
          <div
            onClick={() => toggleAddModal(false)}
            style={{
              position: 'fixed',
              inset: 0,
              background: 'rgba(0,0,0,0.5)',
              zIndex: 1000,
            }}
          />
          <div
            style={{
              position: 'fixed',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              width: 420,
              background: 'white',
              borderRadius: 8,
              padding: 20,
              zIndex: 1001,
              boxShadow: '0 10px 30px rgba(0,0,0,0.25)',
            }}
          >
            <h3 style={{ marginTop: 0 }}>Thêm sản phẩm</h3>
            <form onSubmit={handleAddSave}>
              <div style={{ marginBottom: 15 }}>
                <label style={{ display: 'block', marginBottom: 5, fontWeight: 'bold' }}>Product ID</label>
                <input
                  type="number"
                  required
                  value={addForm.product_id}
                  onChange={(e) => setAddForm((p) => ({ ...p, product_id: e.target.value }))}
                  placeholder="Nhập ID..."
                  style={{ width: '100%', padding: '8px', border: '1px solid #ccc', borderRadius: 4 }}
                />
              </div>
              <div style={{ marginBottom: 15 }}>
                <label style={{ display: 'block', marginBottom: 5 }}>Category</label>
                <input
                  type="number"
                  value={addForm.first_category_id}
                  onChange={(e) => setAddForm((p) => ({ ...p, first_category_id: e.target.value }))}
                  placeholder="Nhập Category..."
                  style={{ width: '100%', padding: '8px', border: '1px solid #ccc', borderRadius: 4 }}
                />
              </div>
              <div style={{ marginBottom: 15 }}>
                <label style={{ display: 'block', marginBottom: 5 }}>Group</label>
                <input
                  type="number"
                  value={addForm.management_group_id}
                  onChange={(e) => setAddForm((p) => ({ ...p, management_group_id: e.target.value }))}
                  placeholder="Nhập Group..."
                  style={{ width: '100%', padding: '8px', border: '1px solid #ccc', borderRadius: 4 }}
                />
              </div>
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 20 }}>
                <button
                  type="button"
                  onClick={() => toggleAddModal(false)}
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
        </>
      )}

      {/* --- FORM MODAL (Hiển thị khi showForm = true) --- */}
      {showForm && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.5)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000
        }}>
          <div className="card" style={{ width: 400, padding: 20 }}>
            <h3>Cập nhật sản phẩm</h3>
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
                      title="Sửa"
                      onClick={() => openEditForm(p)}
                      style={{
                        border: 'none',
                        background: 'none',
                        cursor: 'pointer',
                        fontSize: '16px',
                        marginRight: 10,
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.color = '#1976d2')}
                      onMouseLeave={(e) => (e.currentTarget.style.color = 'inherit')}
                    >
                      ✏️
                    </button>
                    <button
                      title="Xóa"
                      onClick={() => handleDelete(p.product_id)}
                      style={{
                        border: 'none',
                        background: 'none',
                        cursor: 'pointer',
                        fontSize: '16px',
                        color: 'red',
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.color = '#b71c1c')}
                      onMouseLeave={(e) => (e.currentTarget.style.color = 'red')}
                    >
                      🗑️
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