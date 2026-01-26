import { useState, useEffect } from 'react';
import {
  getMonitoredProducts,
  getMonitoredProductDetail,
  addMonitoredProducts,
  deleteMonitoredProduct,
  startFetchTask,
  getFetchTaskStatus,
  fetchSingleProduct,
} from '../services/api';
import type {
  MonitoredProduct,
  SellerSnapshot,
  BulkProductInput,
} from '../services/api';

export default function PriceMonitor() {
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

  useEffect(() => {
    loadProducts();
  }, []);

  useEffect(() => {
    let interval: ReturnType<typeof setInterval> | null = null;
    if (fetchTaskId) {
      interval = setInterval(async () => {
        try {
          const status = await getFetchTaskStatus(fetchTaskId);
          setFetchStatus(status.status);
          setFetchProgress({ completed: status.completed_products, total: status.total_products });
          if (status.status === 'completed') {
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
      const data = await getMonitoredProducts();
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
      const result = await addMonitoredProducts(productList);
      alert(`${result.added} ürün eklendi, ${result.updated} ürün güncellendi.`);
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
      const result = await startFetchTask();
      setFetchTaskId(result.task_id);
      setFetchStatus('started');
    } catch (e) {
      console.error('Error starting fetch:', e);
      alert('Fiyat çekme başlatılamadı');
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

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('tr-TR', { style: 'currency', currency: 'TRY' }).format(price);
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString('tr-TR');
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
          <button
            onClick={handleFetchAll}
            disabled={!!fetchTaskId}
            className="bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 disabled:opacity-50"
          >
            {fetchTaskId ? `Çekiliyor... (${fetchProgress.completed}/${fetchProgress.total})` : 'Tüm Fiyatları Çek'}
          </button>
        </div>
      </div>

      {fetchStatus === 'running' && (
        <div className="bg-blue-100 border border-blue-300 text-blue-800 px-4 py-3 rounded mb-4">
          Fiyatlar çekiliyor: {fetchProgress.completed} / {fetchProgress.total} ürün tamamlandı
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow p-4">
          <h2 className="text-lg font-semibold mb-4">İzlenen Ürünler ({products.length})</h2>
          {loading ? (
            <div className="text-center py-8 text-gray-500">Yükleniyor...</div>
          ) : products.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              Henüz izlenen ürün yok. SKU eklemek için yukarıdaki butonu kullanın.
            </div>
          ) : (
            <div className="space-y-2 max-h-[600px] overflow-y-auto">
              {products.map((product) => (
                <div
                  key={product.id}
                  onClick={() => handleProductClick(product)}
                  className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                    selectedProduct?.id === product.id
                      ? 'border-indigo-500 bg-indigo-50'
                      : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                  }`}
                >
                  <div className="flex justify-between items-start">
                    <div className="flex-1 min-w-0">
                      {product.product_name ? (
                        <a
                          href={product.product_url || `https://www.hepsiburada.com/ara?q=${product.sku}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={(e) => e.stopPropagation()}
                          className="font-medium text-sm text-indigo-600 hover:text-indigo-800 hover:underline truncate block"
                          title={product.product_name}
                        >
                          {product.product_name}
                        </a>
                      ) : (
                        <a
                          href={product.product_url || `https://www.hepsiburada.com/ara?q=${product.sku}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={(e) => e.stopPropagation()}
                          className="font-medium text-sm text-indigo-600 hover:text-indigo-800 hover:underline"
                        >
                          {product.sku}
                        </a>
                      )}
                      {product.product_name && (
                        <div className="text-xs text-gray-500">{product.sku}</div>
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
            {selectedProduct ? `Satıcılar - ${selectedProduct.sku}` : 'Satıcı Detayları'}
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
            <h3 className="text-lg font-semibold mb-4">Ürün Listesi Ekle (JSON)</h3>
            <p className="text-sm text-gray-600 mb-3">
              Aşağıdaki formatta JSON yapıştırın:
            </p>
            <pre className="bg-gray-100 p-2 rounded text-xs mb-3 overflow-x-auto">
{`[
  { "productUrl": "https://www.hepsiburada.com/...-p-SKU123", "productName": "Ürün Adı 1", "sku": "SKU123" },
  { "productUrl": "https://www.hepsiburada.com/...-p-SKU456", "productName": "Ürün Adı 2", "sku": "SKU456" }
]`}
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
