import React from 'react';
import './Products.css';

const Products = () => {
  return (
    <div className="products-page">
      <div className="page-header">
        <h2 className="page-title">Quản lý Sản phẩm</h2>
        <button className="btn btn-primary">+ Thêm sản phẩm</button>
      </div>

      <div className="card">
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Tên sản phẩm</th>
                <th>Mã SKU</th>
                <th>Danh mục</th>
                <th>Tồn kho</th>
                <th>Trạng thái</th>
                <th>Thao tác</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td colSpan="7" className="text-center text-secondary">
                  Chưa có sản phẩm nào
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Products;
