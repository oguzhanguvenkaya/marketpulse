import { useState, useEffect } from 'react';
import { useParams, useSearchParams, useNavigate } from 'react-router-dom';
import { getSellerProducts, exportSellerProducts } from '../services/api';
import type { SellerProduct } from '../services/api';

export default function SellerDetail() {
  const { merchantId } = useParams<{ merchantId: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  
  const platform = (searchParams.get('platform') || 'hepsiburada') as 'hepsiburada' | 'trendyol';
  
  const [products, setProducts] = useState<SellerProduct[]>([]);
  const [merchantName, setMerchantName] = useState('');
  const [loading, setLoading] = useState(true);
  const [priceAlertOnly, setPriceAlertOnly] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    if (merchantId) {
      fetchProducts();
    }
  }, [merchantId, platform, priceAlertOnly]);

  const fetchProducts = async () => {
    if (!merchantId) return;
    setLoading(true);
    try {
      const data = await getSellerProducts(merchantId, platform, priceAlertOnly);
      setProducts(data.products);
      setMerchantName(data.merchant_name);
    } catch (error) {
      console.error('Error fetching seller products:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    if (!merchantId) return;
    setExporting(true);
    try {
      await exportSellerProducts(merchantId, platform, priceAlertOnly);
    } catch (error) {
      console.error('Error exporting:', error);
    } finally {
      setExporting(false);
    }
  };

  const formatPrice = (price?: number) => {
    if (!price) return '-';
    return new Intl.NumberFormat('tr-TR', {
      style: 'currency',
      currency: 'TRY',
      minimumFractionDigits: 2
    }).format(price);
  };

  const filteredProducts = products.filter(product => {
    const searchLower = searchTerm.toLowerCase();
    return (
      (product.product_name?.toLowerCase().includes(searchLower)) ||
      (product.sku?.toLowerCase().includes(searchLower)) ||
      (product.barcode?.toLowerCase().includes(searchLower)) ||
      (product.brand?.toLowerCase().includes(searchLower))
    );
  });

  const alertCount = products.filter(p => p.price_alert).length;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <button
          onClick={() => navigate('/sellers')}
          className="p-2 rounded-lg bg-dark-700 hover:bg-dark-600 transition-colors"
        >
          <svg className="w-5 h-5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        <div>
          <h1 className="text-2xl font-bold text-white">{merchantName || 'Seller'}</h1>
          <p className="text-neutral-400 mt-1">
            {products.length} products • {alertCount} price alerts
          </p>
        </div>
      </div>

      <div className="card-dark p-4">
        <div className="flex flex-wrap items-center gap-4 mb-4">
          <input
            type="text"
            placeholder="Search by name, SKU, barcode, brand..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="input-dark flex-1 min-w-[200px]"
          />
          
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={priceAlertOnly}
              onChange={(e) => setPriceAlertOnly(e.target.checked)}
              className="w-4 h-4 rounded border-dark-600 bg-dark-700 text-accent-primary focus:ring-accent-primary"
            />
            <span className="text-neutral-300 text-sm">Price Alerts Only</span>
            {alertCount > 0 && (
              <span className="badge badge-danger text-xs">{alertCount}</span>
            )}
          </label>

          <button
            onClick={handleExport}
            disabled={exporting || filteredProducts.length === 0}
            className="btn-primary flex items-center gap-2"
          >
            {exporting ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-dark-900"></div>
                Exporting...
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                Export CSV
              </>
            )}
          </button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent-primary"></div>
            <span className="ml-3 text-neutral-400">Loading products...</span>
          </div>
        ) : filteredProducts.length === 0 ? (
          <div className="text-center py-12 text-neutral-400">
            {priceAlertOnly ? 'No products with price alerts' : 'No products found'}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="table-dark w-full">
              <thead>
                <tr>
                  <th className="text-left">Product</th>
                  <th className="text-left">SKU / Barcode</th>
                  <th className="text-left">Brand</th>
                  <th className="text-right">Threshold</th>
                  <th className="text-right">Seller Price</th>
                  <th className="text-right">Difference</th>
                  <th className="text-center">Status</th>
                </tr>
              </thead>
              <tbody>
                {filteredProducts.map((product) => (
                  <tr 
                    key={product.product_id}
                    className={`${product.price_alert ? 'bg-red-900/20' : ''} hover:bg-dark-600 transition-colors`}
                  >
                    <td>
                      <div className="flex items-center gap-3">
                        {product.image_url && (
                          <img
                            src={product.image_url}
                            alt={product.product_name}
                            className="w-10 h-10 rounded object-cover bg-white"
                          />
                        )}
                        <div className="max-w-[300px]">
                          <div className="text-white font-medium truncate" title={product.product_name}>
                            {product.product_name || 'Unnamed Product'}
                          </div>
                          {product.product_url && (
                            <a
                              href={product.product_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-xs text-accent-primary hover:underline"
                            >
                              View on {platform === 'hepsiburada' ? 'HB' : 'Trendyol'}
                            </a>
                          )}
                        </div>
                      </div>
                    </td>
                    <td>
                      <div className="text-neutral-300 text-sm">{product.sku || '-'}</div>
                      <div className="text-neutral-500 text-xs">{product.barcode || '-'}</div>
                    </td>
                    <td className="text-neutral-300">{product.brand || '-'}</td>
                    <td className="text-right text-neutral-300">{formatPrice(product.threshold_price)}</td>
                    <td className="text-right">
                      <div className={`font-semibold ${product.price_alert ? 'text-danger' : 'text-white'}`}>
                        {formatPrice(product.seller_price)}
                      </div>
                      {product.campaign_price && (
                        <div className="text-xs text-orange-400">Sepete Özel</div>
                      )}
                    </td>
                    <td className="text-right">
                      {product.price_difference !== null && product.price_difference !== undefined ? (
                        <span className={`font-medium ${product.price_difference > 0 ? 'text-danger' : 'text-success'}`}>
                          {product.price_difference > 0 ? '-' : '+'}{Math.abs(product.price_difference).toFixed(2)} TL
                        </span>
                      ) : '-'}
                    </td>
                    <td className="text-center">
                      {product.price_alert ? (
                        <span className="badge badge-danger text-xs">Below Threshold</span>
                      ) : (
                        <span className="badge badge-success text-xs">OK</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
