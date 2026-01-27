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
} from '../services/api';
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

  const activeProducts = products.filter(p => p.product_url && p.product_url.trim() !== '');
  const inactiveProducts = products.filter(p => !p.product_url || p.product_url.trim() === '');

  useEffect(() => {
    loadProducts();
  }, [platform]);

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

  const loadProducts = async () => {
    try {
      setLoading(true);
      setSelectedProduct(null);
      setSellers([]);
      const data = await getMonitoredProducts(platform);
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
      alert(`${result.added} ürün eklendi, ${result.updated} ürün güncellendi (${result.platform}).`);
      setShowImportModal(false);
      setImportJson('');
      loadProducts();
    } catch (e: any) {
      alert('JSON parse hatası: ' + e.message);
    } finally {
      setImportLoading(false);
    }
  };

  const handleFetchAll = async () => {
    try {
      const result = await startFetchTask(platform);
      setFetchTaskId(result.task_id);
      setFetchStatus('started');
    } catch (e) {
      console.error('Error starting fetch:', e);
      alert('Fiyat çekme başlatılamadı');
    }
  };

  const handleStopFetch = async () => {
    if (!fetchTaskId) return;
    try {
      await stopFetchTask(fetchTaskId);
      setFetchStatus('stopping');
    } catch (e) {
      console.error('Error stopping fetch:', e);
      alert('Durdurma isteği gönderilemedi');
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
      alert('Fiyat çekilemedi');
    }
  };

  const handleDelete = async (productId: string) => {
    if (!confirm('Bu ürünü silmek istediğinize emin misiniz?')) return;
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

  const handleExport = async () => {
    try {
      setExportLoading(true);
      await exportPriceMonitorData(platform);
    } catch (e) {
      console.error('Error exporting data:', e);
      alert('Veri indirme hatası');
    } finally {
      setExportLoading(false);
    }
  };

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('tr-TR', { style: 'currency', currency: 'TRY' }).format(price);
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString('tr-TR');
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
  { "productUrl": "https://www.trendyol.com/...-p-123456789", "productName": "Ürün Adı 1", "barcode": "8809432676195" },
  { "productUrl": "https://www.trendyol.com/...-p-987654321", "productName": "Ürün Adı 2", "barcode": "8809432671053" }
]`;
    }
    return `[
  { "productUrl": "https://www.hepsiburada.com/...-p-SKU123", "productName": "Ürün Adı 1", "sku": "SKU123" },
  { "productUrl": "https://www.hepsiburada.com/...-p-SKU456", "productName": "Ürün Adı 2", "sku": "SKU456" }
]`;
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Fiyat Takip</h1>
        <div className="flex gap-2">
          <button
            onClick={() => setShowImportModal(true)}
            className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700"
          >
            SKU Ekle
          </button>
          {fetchTaskId ? (
            <>
              <span className="bg-indigo-100 text-indigo-800 px-4 py-2 rounded-lg">
                {fetchStatus === 'stopping' ? 'Durduruluyor...' : `Çekiliyor... (${fetchProgress.completed}/${fetchProgress.total})`}
              </span>
              <button
                onClick={handleStopFetch}
                disabled={fetchStatus === 'stopping'}
                className="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 disabled:opacity-50"
              >
                Durdur
              </button>
            </>
          ) : (
            <button
              onClick={handleFetchAll}
              className="bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700"
            >
              {platform === 'hepsiburada' ? 'Hepsiburada Fiyatları Çek' : 'Trendyol Fiyatları Çek'}
            </button>
          )}
          <button
            onClick={handleExport}
            disabled={exportLoading || products.length === 0}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
          >
            {exportLoading ? 'İndiriliyor...' : 'JSON İndir'}
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
          </button>
        </div>
      </div>

      <div className="flex gap-2 mb-4">
        <button
          onClick={() => setPlatform('hepsiburada')}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            platform === 'hepsiburada'
              ? 'bg-orange-500 text-white'
              : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
          }`}
        >
          Hepsiburada
        </button>
        <button
          onClick={() => setPlatform('trendyol')}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            platform === 'trendyol'
              ? 'bg-orange-500 text-white'
              : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
          }`}
        >
          Trendyol
        </button>
      </div>

      {fetchStatus === 'running' && (
        <div className="bg-blue-100 border border-blue-300 text-blue-800 px-4 py-3 rounded mb-4">
          Fiyatlar çekiliyor: {fetchProgress.completed} / {fetchProgress.total} ürün tamamlandı
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">
              İzlenen Ürünler - {platform === 'hepsiburada' ? 'Hepsiburada' : 'Trendyol'}
            </h2>
            <div className="flex gap-2">
              <button
                onClick={() => setShowInactive(false)}
                className={`px-3 py-1 text-sm rounded-lg font-medium transition-colors ${
                  !showInactive
                    ? 'bg-green-500 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                Aktif ({activeProducts.length})
              </button>
              <button
                onClick={() => setShowInactive(true)}
                className={`px-3 py-1 text-sm rounded-lg font-medium transition-colors ${
                  showInactive
                    ? 'bg-gray-500 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                Pasif ({inactiveProducts.length})
              </button>
            </div>
          </div>
          {loading ? (
            <div className="text-center py-8 text-gray-500">Yükleniyor...</div>
          ) : (showInactive ? inactiveProducts : activeProducts).length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              {showInactive 
                ? 'Pasif ürün bulunmuyor.' 
                : 'Henüz izlenen ürün yok. SKU eklemek için yukarıdaki butonu kullanın.'}
            </div>
          ) : (
            <div className="space-y-2 max-h-[600px] overflow-y-auto">
              {(showInactive ? inactiveProducts : activeProducts).map((product) => (
                <div
                  key={product.id}
                  onClick={() => handleProductClick(product)}
                  className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                    selectedProduct?.id === product.id
                      ? 'border-indigo-500 bg-indigo-50'
                      : showInactive 
                        ? 'border-gray-300 bg-gray-100 hover:bg-gray-200' 
                        : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                  }`}
                >
                  <div className="flex justify-between items-start">
                    <div className="flex-1 min-w-0">
                      {showInactive && (
                        <span className="inline-block bg-gray-500 text-white text-xs px-2 py-0.5 rounded mb-1">
                          Pasif
                        </span>
                      )}
                      {product.product_name ? (
                        showInactive ? (
                          <span className="font-medium text-sm text-gray-500 truncate block" title={product.product_name}>
                            {product.product_name}
                          </span>
                        ) : (
                          <a
                            href={getProductUrl(product)}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="font-medium text-sm text-indigo-600 hover:text-indigo-800 hover:underline truncate block"
                            title={product.product_name}
                          >
                            {product.product_name}
                          </a>
                        )
                      ) : (
                        showInactive ? (
                          <span className="font-medium text-sm text-gray-500">
                            {product.sku}
                          </span>
                        ) : (
                          <a
                            href={getProductUrl(product)}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="font-medium text-sm text-indigo-600 hover:text-indigo-800 hover:underline"
                          >
                            {product.sku}
                          </a>
                        )
                      )}
                      {product.product_name && (
                        <div className="text-xs text-gray-500">
                          {product.barcode ? `Barkod: ${product.barcode}` : `SKU: ${product.sku}`}
                        </div>
                      )}
                      <div className="text-xs text-gray-400 mt-1">
                        {product.seller_count} satıcı
                        {product.last_fetched_at && (
                          <span className="ml-2">• Son: {formatDate(product.last_fetched_at)}</span>
                        )}
                      </div>
                    </div>
                    <div className="flex gap-1 flex-shrink-0">
                      <button
                        onClick={(e) => { e.stopPropagation(); handleFetchSingle(product.id); }}
                        className="text-indigo-600 hover:text-indigo-800 text-xs px-2 py-1"
                        title="Fiyat Çek"
                      >
                        Güncelle
                      </button>
                      <button
                        onClick={(e) => { e.stopPropagation(); handleDelete(product.id); }}
                        className="text-red-600 hover:text-red-800 text-xs px-2 py-1"
                        title="Sil"
                      >
                        Sil
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="bg-white rounded-lg shadow p-4">
          <h2 className="text-lg font-semibold mb-4">
            {selectedProduct ? `Satıcılar - ${selectedProduct.product_name || selectedProduct.sku}` : 'Satıcı Detayları'}
          </h2>
          {!selectedProduct ? (
            <div className="text-center py-8 text-gray-500">
              Satıcıları görmek için sol taraftan bir ürün seçin
            </div>
          ) : sellersLoading ? (
            <div className="text-center py-8 text-gray-500">Yükleniyor...</div>
          ) : sellers.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              Henüz satıcı verisi yok. "Güncelle" butonuna tıklayarak fiyatları çekin.
            </div>
          ) : (
            <div className="space-y-3 max-h-[600px] overflow-y-auto">
              {sellers.map((seller, idx) => (
                <div
                  key={`${seller.merchant_id}-${idx}`}
                  className={`p-3 rounded-lg border ${
                    seller.buybox_order === 1 ? 'border-green-300 bg-green-50' : 'border-gray-200'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    {seller.merchant_logo && (
                      <img
                        src={seller.merchant_logo}
                        alt={seller.merchant_name}
                        className="w-10 h-10 rounded object-contain bg-white border"
                      />
                    )}
                    <div className="flex-1">
                      <div className="flex justify-between items-start">
                        <div>
                          <div className="font-medium text-sm flex items-center gap-2">
                            {seller.merchant_url ? (
                              <a
                                href={seller.merchant_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-indigo-600 hover:text-indigo-800 hover:underline"
                              >
                                {seller.merchant_name}
                              </a>
                            ) : (
                              seller.merchant_name
                            )}
                            {seller.buybox_order === 1 && (
                              <span className="bg-green-500 text-white text-xs px-1.5 py-0.5 rounded">
                                Buybox
                              </span>
                            )}
                          </div>
                          <div className="text-xs text-gray-500 flex items-center gap-2 mt-0.5">
                            {seller.merchant_rating && (
                              <span className="bg-orange-100 text-orange-700 px-1.5 py-0.5 rounded">
                                {seller.merchant_rating.toFixed(1)}
                              </span>
                            )}
                            {seller.merchant_city && <span>{seller.merchant_city}</span>}
                            {seller.stock_quantity !== undefined && (
                              <span>Stok: {seller.stock_quantity}</span>
                            )}
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="font-bold text-lg text-indigo-600">
                            {formatPrice(seller.price)}
                          </div>
                          {seller.original_price && seller.original_price !== seller.price && (
                            <div className="text-xs text-gray-400 line-through">
                              {formatPrice(seller.original_price)}
                            </div>
                          )}
                          {seller.discount_rate && seller.discount_rate > 0 && (
                            <div className="text-xs text-green-600">
                              %{seller.discount_rate.toFixed(0)} indirim
                            </div>
                          )}
                        </div>
                      </div>
                      <div className="flex gap-2 mt-2 text-xs">
                        {seller.free_shipping && (
                          <span className="bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
                            Ücretsiz Kargo
                          </span>
                        )}
                        {seller.fast_shipping && (
                          <span className="bg-purple-100 text-purple-700 px-2 py-0.5 rounded">
                            Hızlı Teslimat
                          </span>
                        )}
                        {seller.is_fulfilled_by_hb && (
                          <span className="bg-orange-100 text-orange-700 px-2 py-0.5 rounded">
                            HepsiBurada Lojistik
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {showImportModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-2xl mx-4">
            <h3 className="text-lg font-semibold mb-4">
              Ürün Listesi Ekle - {platform === 'hepsiburada' ? 'Hepsiburada' : 'Trendyol'} (JSON)
            </h3>
            <p className="text-sm text-gray-600 mb-3">
              Aşağıdaki formatta JSON yapıştırın:
            </p>
            <pre className="bg-gray-100 p-2 rounded text-xs mb-3 overflow-x-auto">
{getImportExample()}
            </pre>
            <textarea
              value={importJson}
              onChange={(e) => setImportJson(e.target.value)}
              className="w-full h-48 border rounded-lg p-3 font-mono text-sm"
              placeholder='[{"productUrl": "...", "sku": "..."}]'
            />
            <div className="flex justify-end gap-2 mt-4">
              <button
                onClick={() => { setShowImportModal(false); setImportJson(''); }}
                className="px-4 py-2 text-gray-600 hover:text-gray-800"
              >
                İptal
              </button>
              <button
                onClick={handleImport}
                disabled={importLoading || !importJson.trim()}
                className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 disabled:opacity-50"
              >
                {importLoading ? 'Ekleniyor...' : 'Ekle'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
