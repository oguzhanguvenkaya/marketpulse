import { useState, useEffect } from 'react';
import {
  getMonitoredProducts,
  getMonitoredProductDetail,
  addMonitoredProducts,
  deleteMonitoredProduct,
  startFetchTask,
  stopFetchTask,
  getFetchTaskStatus,
  fetchSingleProduct,
  exportPriceMonitorData,
  getBrands,
  getLastInactiveSkus,
} from '../services/api';
import type { FetchType, LastInactiveProduct } from '../services/api';
import type {
  MonitoredProduct,
  SellerSnapshot,
  BulkProductInput,
} from '../services/api';

type Platform = 'hepsiburada' | 'trendyol';

export default function PriceMonitor() {
  const [platform, setPlatform] = useState<Platform>('hepsiburada');
  const [products, setProducts] = useState<MonitoredProduct[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedProduct, setSelectedProduct] = useState<MonitoredProduct | null>(null);
  const [sellers, setSellers] = useState<SellerSnapshot[]>([]);
  const [sellersLoading, setSellersLoading] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);
  const [importJson, setImportJson] = useState('');
  const [importLoading, setImportLoading] = useState(false);
  const [fetchTaskId, setFetchTaskId] = useState<string | null>(null);
  const [fetchStatus, setFetchStatus] = useState<string>('');
  const [fetchProgress, setFetchProgress] = useState({ completed: 0, total: 0 });
  const [exportLoading, setExportLoading] = useState(false);
  const [showInactive, setShowInactive] = useState(false);
  const [showExportMenu, setShowExportMenu] = useState(false);
  const [brands, setBrands] = useState<string[]>([]);
  const [selectedBrand, setSelectedBrand] = useState<string>('');
  const [priceAlertOnly, setPriceAlertOnly] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [lastInactiveProducts, setLastInactiveProducts] = useState<LastInactiveProduct[]>([]);
  const [lastInactiveCount, setLastInactiveCount] = useState(0);
  const [showFetchMenu, setShowFetchMenu] = useState(false);
  const [currentFetchType, setCurrentFetchType] = useState<FetchType>('active');

  const activeProducts = products.filter(p => p.is_active !== false && p.seller_count > 0);
  const inactiveProducts = products.filter(p => p.is_active === false || p.seller_count === 0);

  useEffect(() => {
    loadProducts();
    loadBrands();
    loadLastInactive();
  }, [platform]);

  useEffect(() => {
    const handleClickOutside = () => {
      setShowFetchMenu(false);
      setShowExportMenu(false);
    };
    document.addEventListener('click', handleClickOutside);
    return () => document.removeEventListener('click', handleClickOutside);
  }, []);

  const loadLastInactive = async () => {
    try {
      const data = await getLastInactiveSkus(platform);
      setLastInactiveProducts(data.products);
      setLastInactiveCount(data.count);
    } catch (e) {
      console.error('Error loading last inactive:', e);
    }
  };

  useEffect(() => {
    loadProducts();
  }, [selectedBrand, priceAlertOnly, searchQuery]);

  useEffect(() => {
    let interval: ReturnType<typeof setInterval> | null = null;
    if (fetchTaskId) {
      interval = setInterval(async () => {
        try {
          const status = await getFetchTaskStatus(fetchTaskId);
          setFetchStatus(status.status);
          setFetchProgress({ completed: status.completed_products, total: status.total_products });
          if (status.status === 'completed' || status.status === 'stopped' || status.status === 'failed') {
            setFetchTaskId(null);
            loadProducts();
            loadLastInactive();
          }
        } catch (e) {
          console.error('Error checking fetch status:', e);
        }
      }, 2000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [fetchTaskId]);

  const loadBrands = async () => {
    try {
      const data = await getBrands(platform);
      setBrands(data.brands);
    } catch (e) {
      console.error('Error loading brands:', e);
    }
  };

  const loadProducts = async () => {
    try {
      setLoading(true);
      setSelectedProduct(null);
      setSellers([]);
      const params: Record<string, any> = {};
      if (selectedBrand) params.brand = selectedBrand;
      if (priceAlertOnly) params.price_alert_only = true;
      if (searchQuery) params.search = searchQuery;
      const data = await getMonitoredProducts(platform, params);
      setProducts(data.products);
    } catch (e) {
      console.error('Error loading products:', e);
    } finally {
      setLoading(false);
    }
  };

  const handleProductClick = async (product: MonitoredProduct) => {
    setSelectedProduct(product);
    setSellersLoading(true);
    try {
      const data = await getMonitoredProductDetail(product.id);
      setSellers(data.sellers);
    } catch (e) {
      console.error('Error loading sellers:', e);
      setSellers([]);
    } finally {
      setSellersLoading(false);
    }
  };

  const handleImport = async () => {
    try {
      setImportLoading(true);
      const parsed = JSON.parse(importJson);
      const productList: BulkProductInput[] = Array.isArray(parsed) ? parsed : [parsed];
      const result = await addMonitoredProducts(productList, platform);
      alert(`${result.added} products added, ${result.updated} updated (${result.platform}).`);
      setShowImportModal(false);
      setImportJson('');
      loadProducts();
    } catch (e: any) {
      alert('JSON parse error: ' + e.message);
    } finally {
      setImportLoading(false);
    }
  };

  const handleFetchAll = async (fetchType: FetchType = 'active') => {
    try {
      setCurrentFetchType(fetchType);
      setShowFetchMenu(false);
      const result = await startFetchTask(platform, fetchType);
      setFetchTaskId(result.task_id);
      setFetchStatus('started');
    } catch (e) {
      console.error('Error starting fetch:', e);
      alert('Could not start price fetch');
    }
  };

  const handleStopFetch = async () => {
    if (!fetchTaskId) return;
    try {
      await stopFetchTask(fetchTaskId);
      setFetchStatus('stopping');
    } catch (e) {
      console.error('Error stopping fetch:', e);
      alert('Could not stop fetch');
    }
  };

  const handleFetchSingle = async (productId: string) => {
    try {
      await fetchSingleProduct(productId);
      if (selectedProduct?.id === productId) {
        handleProductClick(selectedProduct);
      }
      loadProducts();
    } catch (e) {
      console.error('Error fetching single product:', e);
      alert('Could not fetch price');
    }
  };

  const handleDelete = async (productId: string) => {
    if (!confirm('Are you sure you want to delete this product?')) return;
    try {
      await deleteMonitoredProduct(productId);
      if (selectedProduct?.id === productId) {
        setSelectedProduct(null);
        setSellers([]);
      }
      loadProducts();
    } catch (e) {
      console.error('Error deleting product:', e);
    }
  };

  const handleExport = async (filter: 'all' | 'active' | 'inactive' = 'all') => {
    try {
      setExportLoading(true);
      setShowExportMenu(false);
      await exportPriceMonitorData(platform, filter);
    } catch (e) {
      console.error('Error exporting data:', e);
      alert('Export failed');
    } finally {
      setExportLoading(false);
    }
  };

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('tr-TR', { style: 'currency', currency: 'TRY' }).format(price);
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  const getProductUrl = (product: MonitoredProduct) => {
    if (product.product_url) return product.product_url;
    if (product.platform === 'trendyol') {
      return `https://www.trendyol.com/arama?q=${product.sku}`;
    }
    return `https://www.hepsiburada.com/ara?q=${product.sku}`;
  };

  const getImportExample = () => {
    if (platform === 'trendyol') {
      return `[
  {
    "productUrl": "https://www.trendyol.com/...-p-123456789",
    "productName": "Product Name",
    "barcode": "8809432676195",
    "brand": "Brand Name",
    "price": 299.99,
    "sellerStockCode": "STK001"
  }
]`;
    }
    return `[
  {
    "productUrl": "https://www.hepsiburada.com/...-p-SKU123",
    "productName": "Product Name",
    "sku": "SKU123",
    "brand": "Brand Name",
    "price": 299.99,
    "sellerStockCode": "STK001"
  }
]`;
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Price Monitor</h1>
          <p className="text-neutral-400 mt-1">Track seller prices and identify violations</p>
        </div>
        <div className="flex gap-3">
          <button onClick={() => setShowImportModal(true)} className="btn-secondary flex items-center gap-2">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Add SKU
          </button>
          {fetchTaskId ? (
            <>
              <div className="px-4 py-2 rounded-lg bg-accent-primary/10 border border-accent-primary/20 text-accent-primary text-sm flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-accent-primary animate-pulse" />
                {fetchStatus === 'stopping' ? 'Stopping...' : `Fetching ${currentFetchType === 'last_inactive' ? 'last inactive' : currentFetchType}... (${fetchProgress.completed}/${fetchProgress.total})`}
              </div>
              <button onClick={handleStopFetch} disabled={fetchStatus === 'stopping'} className="btn-danger">
                Stop
              </button>
            </>
          ) : (
            <div className="relative">
              <button 
                onClick={(e) => { e.stopPropagation(); setShowFetchMenu(!showFetchMenu); }} 
                disabled={activeProducts.length === 0 && inactiveProducts.length === 0 && lastInactiveCount === 0} 
                className="btn-primary flex items-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Fetch Prices
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>
              {showFetchMenu && (
                <div className="absolute right-0 mt-2 w-56 card-dark border border-white/10 z-20 overflow-hidden">
                  <button 
                    onClick={() => handleFetchAll('active')} 
                    disabled={activeProducts.length === 0}
                    className="w-full text-left px-4 py-3 text-sm text-neutral-200 hover:bg-white/5 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <div className="font-medium">Active Products</div>
                    <div className="text-xs text-neutral-400">{activeProducts.length} products</div>
                  </button>
                  <button 
                    onClick={() => handleFetchAll('last_inactive')} 
                    disabled={lastInactiveCount === 0}
                    className="w-full text-left px-4 py-3 text-sm text-neutral-200 hover:bg-white/5 transition-colors border-t border-white/5 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <div className="font-medium text-orange-400">Last Inactive</div>
                    <div className="text-xs text-neutral-400">{lastInactiveCount} SKUs from last fetch</div>
                  </button>
                  <button 
                    onClick={() => handleFetchAll('inactive')} 
                    disabled={inactiveProducts.length === 0}
                    className="w-full text-left px-4 py-3 text-sm text-neutral-200 hover:bg-white/5 transition-colors border-t border-white/5 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <div className="font-medium text-red-400">All Inactive</div>
                    <div className="text-xs text-neutral-400">{inactiveProducts.length} products</div>
                  </button>
                </div>
              )}
            </div>
          )}
          <div className="relative">
            <button
              onClick={(e) => { e.stopPropagation(); setShowExportMenu(!showExportMenu); }}
              disabled={exportLoading || products.length === 0}
              className="btn-secondary flex items-center gap-2"
            >
              {exportLoading ? 'Exporting...' : 'Export'}
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            {showExportMenu && (
              <div className="absolute right-0 mt-2 w-48 card-dark border border-white/10 z-20 overflow-hidden">
                <button onClick={() => handleExport('all')} className="w-full text-left px-4 py-3 text-sm text-neutral-200 hover:bg-white/5 transition-colors">
                  All ({products.length})
                </button>
                <button onClick={() => handleExport('active')} className="w-full text-left px-4 py-3 text-sm text-neutral-200 hover:bg-white/5 transition-colors">
                  Active Only ({activeProducts.length})
                </button>
                <button onClick={() => handleExport('inactive')} className="w-full text-left px-4 py-3 text-sm text-neutral-200 hover:bg-white/5 transition-colors">
                  Inactive Only ({inactiveProducts.length})
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="flex gap-2">
        <button
          onClick={() => setPlatform('hepsiburada')}
          className={`px-4 py-2 rounded-lg font-medium text-sm transition-all ${
            platform === 'hepsiburada'
              ? 'bg-[#ff6000] text-white shadow-glow-orange'
              : 'bg-dark-600 text-neutral-300 hover:bg-dark-500'
          }`}
        >
          Hepsiburada
        </button>
        <button
          onClick={() => setPlatform('trendyol')}
          className={`px-4 py-2 rounded-lg font-medium text-sm transition-all ${
            platform === 'trendyol'
              ? 'bg-[#ff6000] text-white shadow-glow-orange'
              : 'bg-dark-600 text-neutral-300 hover:bg-dark-500'
          }`}
        >
          Trendyol
        </button>
      </div>

      {fetchStatus === 'running' && (
        <div className="p-4 rounded-lg bg-accent-primary/5 border border-accent-primary/20">
          <div className="flex items-center gap-3">
            <div className="w-2 h-2 rounded-full bg-accent-primary animate-pulse" />
            <span className="text-accent-primary">Fetching prices: {fetchProgress.completed} / {fetchProgress.total} products completed</span>
          </div>
          <div className="mt-2 progress-bar">
            <div className="progress-bar-fill" style={{ width: `${(fetchProgress.completed / fetchProgress.total) * 100}%` }} />
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card-dark p-5">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-accent-primary/10 flex items-center justify-center">
                <svg className="w-4 h-4 text-accent-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
              </div>
              <h2 className="text-lg font-semibold text-white">Monitored Products</h2>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setShowInactive(false)}
                className={`px-3 py-1.5 text-xs rounded-lg font-medium transition-all ${
                  !showInactive ? 'bg-success/20 text-success border border-success/30' : 'bg-dark-600 text-neutral-400 hover:bg-dark-500'
                }`}
              >
                Active ({activeProducts.length})
              </button>
              <button
                onClick={() => setShowInactive(true)}
                className={`px-3 py-1.5 text-xs rounded-lg font-medium transition-all ${
                  showInactive ? 'bg-neutral-500/20 text-neutral-300 border border-neutral-500/30' : 'bg-dark-600 text-neutral-400 hover:bg-dark-500'
                }`}
              >
                Inactive ({inactiveProducts.length})
              </button>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row gap-2 mb-4">
            <input
              type="text"
              placeholder="Search by SKU, barcode, stock code or name..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="input-dark flex-1 text-sm"
            />
            <select
              value={selectedBrand}
              onChange={(e) => setSelectedBrand(e.target.value)}
              className="input-dark text-sm min-w-[140px]"
            >
              <option value="">All Brands</option>
              {brands.map(brand => (
                <option key={brand} value={brand}>{brand}</option>
              ))}
            </select>
            <button
              onClick={() => setPriceAlertOnly(!priceAlertOnly)}
              className={`px-3 py-2 text-sm rounded-lg font-medium transition-all whitespace-nowrap ${
                priceAlertOnly
                  ? 'bg-danger/20 text-danger border border-danger/30'
                  : 'bg-dark-600 text-neutral-400 hover:bg-dark-500'
              }`}
            >
              Price Alerts
            </button>
          </div>

          {loading ? (
            <div className="text-center py-12">
              <div className="w-8 h-8 border-2 border-accent-primary/30 border-t-accent-primary rounded-full animate-spin mx-auto" />
              <p className="text-neutral-500 mt-3">Loading products...</p>
            </div>
          ) : (showInactive ? inactiveProducts : activeProducts).length === 0 ? (
            <div className="text-center py-12">
              <div className="w-12 h-12 rounded-full bg-dark-600 flex items-center justify-center mx-auto mb-4">
                <svg className="w-6 h-6 text-neutral-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
                </svg>
              </div>
              <p className="text-neutral-400">{showInactive ? 'No inactive products' : 'No monitored products yet'}</p>
              <p className="text-sm text-neutral-500 mt-1">{showInactive ? '' : 'Click "Add SKU" to start monitoring'}</p>
            </div>
          ) : (
            <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
              {(showInactive ? inactiveProducts : activeProducts).map((product) => (
                <div
                  key={product.id}
                  onClick={() => handleProductClick(product)}
                  className={`p-4 rounded-lg border cursor-pointer transition-all ${
                    selectedProduct?.id === product.id
                      ? 'border-accent-primary/50 bg-accent-primary/5'
                      : showInactive
                        ? 'border-white/5 bg-dark-700/50 hover:bg-dark-600/50'
                        : 'border-white/5 bg-dark-700/30 hover:border-white/10 hover:bg-dark-600/30'
                  }`}
                >
                  <div className="flex justify-between items-start">
                    <div className="flex-1 min-w-0">
                      <div className="flex gap-1.5 mb-2 flex-wrap">
                        {showInactive && (
                          <span className="badge badge-neutral">Inactive</span>
                        )}
                        {product.has_price_alert && (
                          <span className="badge badge-danger">
                            Alert ({product.price_alert_count})
                          </span>
                        )}
                        {product.brand && (
                          <span className="badge badge-info">{product.brand}</span>
                        )}
                      </div>
                      {product.product_name ? (
                        showInactive ? (
                          <span className="font-medium text-sm text-neutral-500 truncate block">{product.product_name}</span>
                        ) : (
                          <a
                            href={getProductUrl(product)}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="font-medium text-sm text-accent-primary hover:text-accent-primary/80 truncate block"
                          >
                            {product.product_name}
                          </a>
                        )
                      ) : (
                        showInactive ? (
                          <span className="font-medium text-sm text-neutral-500">{product.sku}</span>
                        ) : (
                          <a
                            href={getProductUrl(product)}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="font-medium text-sm text-accent-primary hover:text-accent-primary/80"
                          >
                            {product.sku}
                          </a>
                        )
                      )}
                      {product.product_name && (
                        <div className="text-xs text-neutral-500 mt-1">
                          {product.barcode ? `Barcode: ${product.barcode}` : `SKU: ${product.sku}`}
                        </div>
                      )}
                      <div className="text-xs text-neutral-500 mt-1 flex items-center gap-2">
                        <span>{product.seller_count} sellers</span>
                        {product.last_fetched_at && (
                          <>
                            <span className="text-neutral-600">•</span>
                            <span>Last: {formatDate(product.last_fetched_at)}</span>
                          </>
                        )}
                      </div>
                    </div>
                    <div className="flex gap-1 flex-shrink-0">
                      <button
                        onClick={(e) => { e.stopPropagation(); handleFetchSingle(product.id); }}
                        className="text-accent-primary hover:text-accent-primary/80 text-xs px-2 py-1 rounded hover:bg-accent-primary/10 transition-colors cursor-pointer"
                      >
                        Refresh
                      </button>
                      <button
                        onClick={(e) => { e.stopPropagation(); handleDelete(product.id); }}
                        className="text-danger hover:text-danger/80 text-xs px-2 py-1 rounded hover:bg-danger/10 transition-colors cursor-pointer"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="card-dark p-5">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-8 h-8 rounded-lg bg-accent-primary/10 flex items-center justify-center">
              <svg className="w-4 h-4 text-accent-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
              </svg>
            </div>
            <h2 className="text-lg font-semibold text-white">
              {selectedProduct ? `Sellers - ${selectedProduct.product_name || selectedProduct.sku}` : 'Seller Details'}
            </h2>
          </div>

          {selectedProduct && (
            <div className="flex flex-wrap gap-2 mb-4">
              {selectedProduct.threshold_price && (
                <span className="badge badge-warning">
                  Threshold: {selectedProduct.threshold_price.toLocaleString('tr-TR')} TL
                </span>
              )}
              {selectedProduct.seller_stock_code && (
                <span className="badge badge-neutral">
                  Stock Code: {selectedProduct.seller_stock_code}
                </span>
              )}
              {selectedProduct.brand && (
                <span className="badge badge-info">
                  Brand: {selectedProduct.brand}
                </span>
              )}
            </div>
          )}

          {!selectedProduct ? (
            <div className="text-center py-12">
              <div className="w-12 h-12 rounded-full bg-dark-600 flex items-center justify-center mx-auto mb-4">
                <svg className="w-6 h-6 text-neutral-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 4.05l-2.122 2.122m-5.657 5.656l-2.12 2.122" />
                </svg>
              </div>
              <p className="text-neutral-400">Select a product to view sellers</p>
            </div>
          ) : sellersLoading ? (
            <div className="text-center py-12">
              <div className="w-8 h-8 border-2 border-accent-primary/30 border-t-accent-primary rounded-full animate-spin mx-auto" />
              <p className="text-neutral-500 mt-3">Loading sellers...</p>
            </div>
          ) : sellers.length === 0 ? (
            <div className="text-center py-12">
              <div className="w-12 h-12 rounded-full bg-dark-600 flex items-center justify-center mx-auto mb-4">
                <svg className="w-6 h-6 text-neutral-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
                </svg>
              </div>
              <p className="text-neutral-400">No seller data yet</p>
              <p className="text-sm text-neutral-500 mt-1">Click "Refresh" to fetch prices</p>
            </div>
          ) : (
            <div className="space-y-3 max-h-[600px] overflow-y-auto pr-1">
              {sellers.map((seller, idx) => {
                const lowestPrice = Math.min(...sellers.map(s => s.price));
                const isLowestPrice = seller.price === lowestPrice;
                return (
                <div
                  key={`${seller.merchant_id}-${idx}`}
                  className={`p-4 rounded-lg transition-all cursor-pointer hover:bg-[#555555] ${
                    seller.price_alert
                      ? 'bg-red-900/40'
                      : seller.buybox_order === 1
                        ? 'bg-green-900/40'
                        : 'bg-[#3a3a3a]'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    {seller.merchant_logo && (
                      <img
                        src={seller.merchant_logo}
                        alt={seller.merchant_name}
                        className="w-10 h-10 rounded-lg object-contain bg-white border border-white/10"
                      />
                    )}
                    <div className="flex-1 min-w-0">
                      <div className="flex justify-between items-start">
                        <div>
                          <div className="font-medium text-sm flex items-center gap-2 flex-wrap">
                            {seller.merchant_url ? (
                              <a
                                href={seller.merchant_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-white hover:text-accent-primary transition-colors font-semibold"
                              >
                                {seller.merchant_name}
                              </a>
                            ) : (
                              <span className="text-white font-semibold">{seller.merchant_name}</span>
                            )}
                            {seller.buybox_order === 1 && (
                              <span className="text-[10px] px-2 py-0.5 rounded-full bg-success/20 text-success">Buybox</span>
                            )}
                            {isLowestPrice && (
                              <span className="text-[10px] px-2 py-0.5 rounded-full bg-accent-primary/20 text-accent-primary">Lowest Price</span>
                            )}
                            {seller.price_alert && (
                              <span className="badge badge-danger text-[10px]">Below Threshold</span>
                            )}
                          </div>
                          <div className="flex items-center gap-2 mt-1 text-xs text-neutral-300">
                            {seller.merchant_rating && (
                              <span className="px-1.5 py-0.5 rounded bg-warning/20 text-warning font-medium">
                                {seller.merchant_rating.toFixed(1)}
                              </span>
                            )}
                            {seller.merchant_city && <span>{seller.merchant_city}</span>}
                            {seller.stock_quantity !== undefined && (
                              <span>Stock: {seller.stock_quantity}</span>
                            )}
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="font-bold text-lg text-white flex items-center gap-2 justify-end">
                            {formatPrice(seller.price)}
                            {seller.campaign_price && (
                              <span className="text-[10px] px-1.5 py-0.5 rounded bg-orange-500/20 text-orange-400 border border-orange-500/30 animate-pulse">
                                Sepete Özel
                              </span>
                            )}
                          </div>
                          {seller.original_price && seller.original_price !== seller.price && (
                            <div className="text-xs text-neutral-400 line-through">
                              {formatPrice(seller.original_price)}
                            </div>
                          )}
                          {seller.discount_rate && seller.discount_rate > 0 && (
                            <div className="text-xs text-success font-medium">
                              %{seller.discount_rate.toFixed(0)} off
                            </div>
                          )}
                        </div>
                      </div>
                      <div className="flex flex-wrap gap-1.5 mt-3">
                        {seller.free_shipping && (
                          <span className="text-[10px] px-2 py-0.5 rounded-full bg-accent-primary/10 text-accent-primary border border-accent-primary/20">
                            Free Shipping
                          </span>
                        )}
                        {seller.fast_shipping && (
                          <span className="text-[10px] px-2 py-0.5 rounded-full bg-purple-500/10 text-purple-400 border border-purple-500/20">
                            Fast Delivery
                          </span>
                        )}
                        {seller.is_fulfilled_by_hb && (
                          <span className="text-[10px] px-2 py-0.5 rounded-full bg-warning/10 text-warning border border-warning/20">
                            HB Logistics
                          </span>
                        )}
                      </div>
                      {seller.campaigns && seller.campaigns.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-2">
                          {seller.campaigns.map((campaign, idx) => (
                            <span
                              key={idx}
                              className="text-[10px] px-2 py-0.5 rounded-full bg-warning/15 text-warning border border-warning/30"
                            >
                              {campaign}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              );
              })}
            </div>
          )}
        </div>
      </div>

      {showImportModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="card-dark border border-white/10 p-6 w-full max-w-2xl mx-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-white">
                Import Products - {platform === 'hepsiburada' ? 'Hepsiburada' : 'Trendyol'}
              </h3>
              <button
                onClick={() => { setShowImportModal(false); setImportJson(''); }}
                className="text-neutral-400 hover:text-white transition-colors"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <p className="text-sm text-neutral-400 mb-3">Paste JSON in the following format:</p>
            <pre className="bg-dark-900 p-3 rounded-lg text-xs text-neutral-300 mb-4 overflow-x-auto border border-white/5">
              {getImportExample()}
            </pre>
            <textarea
              value={importJson}
              onChange={(e) => setImportJson(e.target.value)}
              className="input-dark w-full h-48 font-mono text-sm resize-none"
              placeholder='[{"productUrl": "...", "sku": "..."}]'
            />
            <div className="flex justify-end gap-3 mt-4">
              <button
                onClick={() => { setShowImportModal(false); setImportJson(''); }}
                className="btn-secondary"
              >
                Cancel
              </button>
              <button
                onClick={handleImport}
                disabled={importLoading || !importJson.trim()}
                className="btn-primary"
              >
                {importLoading ? 'Importing...' : 'Import'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
