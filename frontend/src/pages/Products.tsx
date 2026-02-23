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
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
    <div className="space-y-5 md:space-y-6 animate-fade-in">
      <div className="mb-2">
        <div>
          <h1 className="text-xl md:text-2xl font-bold text-text-primary">Products</h1>
          <p className="text-sm md:text-base text-text-muted mt-1">Browse and analyze collected product data</p>
        </div>
      </div>

      <div className="card-dark p-4 md:p-5">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-8 h-8 rounded-lg bg-accent-primary/10 flex items-center justify-center">
            <svg className="w-4 h-4 text-accent-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
            </svg>
          </div>
          <h2 className="text-lg font-semibold text-text-primary">Filter Products</h2>
        </div>
        <form onSubmit={handleSearch} className="flex flex-col md:flex-row gap-3 md:gap-4">
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Filter by product name..."
            className="input-dark flex-1"
          />
          <select
            value={platform}
            onChange={(e) => setPlatform(e.target.value)}
            className="input-dark w-full md:w-auto md:min-w-[180px]"
          >
            <option value="">All Platforms</option>
            <option value="hepsiburada">Hepsiburada</option>
            <option value="trendyol">Trendyol</option>
            <option value="amazon">Amazon</option>
          </select>
          <button type="submit" className="btn-primary w-full md:w-auto flex items-center justify-center">
            Filter
          </button>
        </form>
      </div>

      {loading ? (
        <div className="card-dark p-10 md:p-12 text-center">
          <div className="w-10 h-10 border-2 border-accent-primary/30 border-t-accent-primary rounded-full animate-spin mx-auto" />
          <p className="mt-4 text-text-muted">Loading products...</p>
        </div>
      ) : products.length === 0 ? (
        <div className="card-dark p-10 md:p-12 text-center">
          <div className="w-12 h-12 rounded-full bg-surface-hover flex items-center justify-center mx-auto mb-4">
            <svg className="w-6 h-6 text-neutral-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
            </svg>
          </div>
          <p className="text-text-muted">No products found yet</p>
          <p className="text-sm text-neutral-500 mt-1">Start a search from Dashboard to collect data</p>
        </div>
      ) : (
        <div className="card-dark overflow-hidden">
          <div className="overflow-x-auto">
          <table className="table-dark min-w-[760px]">
            <thead>
              <tr>
                <th>Product</th>
                <th>Platform</th>
                <th>Price</th>
                <th>Rating</th>
                <th>Reviews</th>
                <th>Sponsored</th>
              </tr>
            </thead>
            <tbody>
              {products.map((product) => (
                <tr key={product.id}>
                  <td>
                    <Link to={`/products/${product.id}`} className="flex items-center gap-3 group">
                      {product.image_url ? (
                        <img src={product.image_url} alt="" className="w-12 h-12 object-cover rounded-lg border border-accent-primary/12" />
                      ) : (
                        <div className="w-12 h-12 rounded-lg bg-surface-hover flex items-center justify-center">
                          <svg className="w-5 h-5 text-neutral-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                          </svg>
                        </div>
                      )}
                      <div className="min-w-0">
                        <div className="font-medium text-sm text-text-secondary group-hover:text-accent-primary transition-colors line-clamp-2">
                          {product.name}
                        </div>
                        {product.seller_name && (
                          <div className="text-xs text-neutral-500">{product.seller_name}</div>
                        )}
                      </div>
                    </Link>
                  </td>
                  <td>
                    <span className="badge badge-neutral capitalize">{product.platform}</span>
                  </td>
                  <td className="font-medium text-success">
                    {formatPrice(product.latest_price)}
                  </td>
                  <td>
                    {product.latest_rating ? (
                      <span className="flex items-center gap-1.5">
                        <span className="text-warning">
                          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                          </svg>
                        </span>
                        <span className="text-text-secondary">{product.latest_rating.toFixed(1)}</span>
                      </span>
                    ) : (
                      <span className="text-neutral-500">-</span>
                    )}
                  </td>
                  <td className="text-text-muted">
                    {product.reviews_count || 0}
                  </td>
                  <td>
                    {product.is_sponsored ? (
                      <span className="badge badge-warning">Sponsored</span>
                    ) : (
                      <span className="text-text-faded">-</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        </div>
      )}
    </div>
  );
}
