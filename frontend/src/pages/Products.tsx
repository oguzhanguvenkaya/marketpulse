import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getProducts } from '../services/api';
import type { Product } from '../services/api';

export default function Products() {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [platform, setPlatform] = useState('');

  useEffect(() => {
    loadProducts();
  }, []);

  const loadProducts = async () => {
    setLoading(true);
    try {
      const data = await getProducts(searchTerm || undefined, platform || undefined, 100);
      setProducts(data);
    } catch (error) {
      console.error('Error loading products:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    loadProducts();
  };

  const formatPrice = (price?: number) => {
    if (!price) return '-';
    return new Intl.NumberFormat('tr-TR', { style: 'currency', currency: 'TRY' }).format(price);
  };

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-bold text-gray-800 mb-4">📦 Ürün Listesi</h2>
        <form onSubmit={handleSearch} className="flex gap-4">
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Ürün adı ile filtrele..."
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
          <select
            value={platform}
            onChange={(e) => setPlatform(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">Tüm Platformlar</option>
            <option value="hepsiburada">Hepsiburada</option>
            <option value="trendyol">Trendyol</option>
            <option value="amazon">Amazon</option>
          </select>
          <button
            type="submit"
            className="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
          >
            Filtrele
          </button>
        </form>
      </div>

      {loading ? (
        <div className="bg-white rounded-lg shadow p-8 text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
          <p className="mt-4 text-gray-500">Ürünler yükleniyor...</p>
        </div>
      ) : products.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
          Henüz ürün bulunamadı. Dashboard'dan arama yaparak başlayın.
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Ürün</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Platform</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Fiyat</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Puan</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Yorumlar</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Sponsorlu</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {products.map((product) => (
                <tr key={product.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <Link to={`/products/${product.id}`} className="flex items-center gap-3 hover:text-indigo-600">
                      {product.image_url && (
                        <img src={product.image_url} alt="" className="w-12 h-12 object-cover rounded" />
                      )}
                      <div>
                        <div className="font-medium text-sm line-clamp-2">{product.name}</div>
                        {product.seller_name && (
                          <div className="text-xs text-gray-500">{product.seller_name}</div>
                        )}
                      </div>
                    </Link>
                  </td>
                  <td className="px-6 py-4">
                    <span className="px-2 py-1 bg-gray-100 rounded text-sm">{product.platform}</span>
                  </td>
                  <td className="px-6 py-4 font-medium text-green-600">
                    {formatPrice(product.latest_price)}
                  </td>
                  <td className="px-6 py-4">
                    {product.latest_rating ? (
                      <span className="flex items-center gap-1">
                        <span className="text-yellow-500">⭐</span>
                        {product.latest_rating.toFixed(1)}
                      </span>
                    ) : '-'}
                  </td>
                  <td className="px-6 py-4 text-gray-600">
                    {product.reviews_count || 0}
                  </td>
                  <td className="px-6 py-4">
                    {product.is_sponsored ? (
                      <span className="px-2 py-1 bg-orange-100 text-orange-800 rounded text-xs">Sponsorlu</span>
                    ) : (
                      <span className="text-gray-400">-</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
