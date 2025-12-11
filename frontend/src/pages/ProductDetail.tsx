import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import Plot from 'react-plotly.js';
import { getProduct, getProductSnapshots, analyzeProducts } from '../services/api';
import type { ProductDetail as ProductDetailType, Snapshot } from '../services/api';

export default function ProductDetail() {
  const { id } = useParams<{ id: string }>();
  const [product, setProduct] = useState<ProductDetailType | null>(null);
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysis, setAnalysis] = useState<string | null>(null);
  const [question, setQuestion] = useState('');
  const [activeTab, setActiveTab] = useState<'info' | 'sellers' | 'reviews'>('info');

  useEffect(() => {
    if (id) {
      loadData();
    }
  }, [id]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [productData, snapshotsData] = await Promise.all([
        getProduct(id!),
        getProductSnapshots(id!, 30)
      ]);
      setProduct(productData);
      setSnapshots(snapshotsData);
    } catch (error) {
      console.error('Error loading product:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyze = async () => {
    if (!id) return;
    setAnalyzing(true);
    try {
      const result = await analyzeProducts([id], question || undefined);
      setAnalysis(result.analysis);
    } catch (error) {
      console.error('Error analyzing:', error);
    } finally {
      setAnalyzing(false);
    }
  };

  const formatPrice = (price?: number) => {
    if (!price) return '-';
    return new Intl.NumberFormat('tr-TR', { style: 'currency', currency: 'TRY' }).format(price);
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-8 text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
        <p className="mt-4 text-gray-500">Yukleniyor...</p>
      </div>
    );
  }

  if (!product) {
    return (
      <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
        Urun bulunamadi
      </div>
    );
  }

  const priceData = {
    x: snapshots.map(s => s.snapshot_date),
    y: snapshots.map(s => s.price || 0),
    type: 'scatter' as const,
    mode: 'lines+markers' as const,
    name: 'Fiyat',
    line: { color: '#4F46E5' }
  };

  const ratingData = {
    x: snapshots.map(s => s.snapshot_date),
    y: snapshots.map(s => s.rating || 0),
    type: 'scatter' as const,
    mode: 'lines+markers' as const,
    name: 'Puan',
    line: { color: '#10B981' }
  };

  const hasDiscount = product.discounted_price && product.latest_price && product.discounted_price < product.latest_price;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 text-sm text-gray-500">
        <Link to="/products" className="hover:text-indigo-600">Urunler</Link>
        <span>/</span>
        <span>Detay</span>
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex gap-6">
          {product.image_url && (
            <img src={product.image_url} alt="" className="w-48 h-48 object-cover rounded-lg" />
          )}
          <div className="flex-1">
            {product.brand && (
              <span className="text-sm text-indigo-600 font-medium">{product.brand}</span>
            )}
            <h1 className="text-2xl font-bold text-gray-800 mb-2">{product.name}</h1>
            
            <div className="space-y-1 text-gray-600 text-sm">
              <p><span className="font-medium">Platform:</span> {product.platform}</p>
              {product.seller_name && (
                <p>
                  <span className="font-medium">Satici:</span> {product.seller_name}
                  {product.seller_rating && (
                    <span className="ml-2 text-yellow-600">({product.seller_rating.toFixed(1)} puan)</span>
                  )}
                </p>
              )}
              {product.category_hierarchy && <p><span className="font-medium">Kategori:</span> {product.category_hierarchy}</p>}
              {product.origin_country && <p><span className="font-medium">Mensei:</span> {product.origin_country}</p>}
              {product.sku && <p><span className="font-medium">SKU:</span> {product.sku}</p>}
              {product.barcode && <p><span className="font-medium">Barkod:</span> {product.barcode}</p>}
            </div>

            <div className="mt-4 flex flex-wrap gap-3">
              <div className="bg-green-50 px-4 py-2 rounded-lg">
                {hasDiscount ? (
                  <>
                    <div className="text-lg line-through text-gray-400">{formatPrice(product.latest_price)}</div>
                    <div className="text-2xl font-bold text-green-600">{formatPrice(product.discounted_price)}</div>
                  </>
                ) : (
                  <div className="text-2xl font-bold text-green-600">{formatPrice(product.latest_price)}</div>
                )}
                <div className="text-sm text-gray-500">Guncel Fiyat</div>
              </div>
              <div className="bg-yellow-50 px-4 py-2 rounded-lg">
                <div className="text-2xl font-bold text-yellow-600">
                  {product.latest_rating ? product.latest_rating.toFixed(1) : '-'}
                </div>
                <div className="text-sm text-gray-500">Puan</div>
              </div>
              <div className="bg-blue-50 px-4 py-2 rounded-lg">
                <div className="text-2xl font-bold text-blue-600">{product.reviews_count || 0}</div>
                <div className="text-sm text-gray-500">Yorum</div>
              </div>
              <div className="bg-purple-50 px-4 py-2 rounded-lg">
                <div className="text-2xl font-bold text-purple-600">
                  {product.stock_count ? (product.stock_count < 50 ? `<${product.stock_count}` : product.stock_count) : (product.in_stock ? 'Var' : 'Yok')}
                </div>
                <div className="text-sm text-gray-500">Stok</div>
              </div>
            </div>

            {(product.coupons && product.coupons.length > 0) && (
              <div className="mt-4">
                <h3 className="font-medium text-gray-700 mb-2">Kuponlar</h3>
                <div className="flex flex-wrap gap-2">
                  {product.coupons.map((coupon, i) => (
                    <span key={i} className="bg-red-100 text-red-700 px-3 py-1 rounded-full text-sm">
                      {coupon.amount} TL {coupon.min_order && `(min: ${coupon.min_order} TL)`}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {(product.campaigns && product.campaigns.length > 0) && (
              <div className="mt-4">
                <h3 className="font-medium text-gray-700 mb-2">Kampanyalar</h3>
                <div className="flex flex-wrap gap-2">
                  {product.campaigns.map((campaign, i) => (
                    <span key={i} className="bg-orange-100 text-orange-700 px-3 py-1 rounded-full text-sm">
                      {campaign.name}
                    </span>
                  ))}
                </div>
              </div>
            )}

            <a
              href={product.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-block mt-4 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
            >
              Pazaryerinde Goruntule
            </a>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow">
        <div className="border-b">
          <nav className="flex -mb-px">
            <button
              onClick={() => setActiveTab('info')}
              className={`px-6 py-3 border-b-2 font-medium text-sm ${
                activeTab === 'info' ? 'border-indigo-500 text-indigo-600' : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              Urun Bilgileri
            </button>
            <button
              onClick={() => setActiveTab('sellers')}
              className={`px-6 py-3 border-b-2 font-medium text-sm ${
                activeTab === 'sellers' ? 'border-indigo-500 text-indigo-600' : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              Diger Saticilar ({product.other_sellers?.length || 0})
            </button>
            <button
              onClick={() => setActiveTab('reviews')}
              className={`px-6 py-3 border-b-2 font-medium text-sm ${
                activeTab === 'reviews' ? 'border-indigo-500 text-indigo-600' : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              Yorumlar ({product.reviews?.length || 0})
            </button>
          </nav>
        </div>

        <div className="p-6">
          {activeTab === 'info' && (
            <div>
              {product.description ? (
                <div className="prose max-w-none">
                  <p className="text-gray-600 whitespace-pre-wrap">{product.description}</p>
                </div>
              ) : (
                <p className="text-gray-500">Urun aciklamasi bulunamadi.</p>
              )}
            </div>
          )}

          {activeTab === 'sellers' && (
            <div>
              {product.other_sellers && product.other_sellers.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="bg-gray-50">
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">Satici</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">Puan</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">Fiyat</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">Yetkili</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {product.other_sellers.map((seller, i) => (
                        <tr key={i}>
                          <td className="px-4 py-3 text-sm text-gray-800">{seller.seller_name}</td>
                          <td className="px-4 py-3 text-sm text-yellow-600">
                            {seller.seller_rating ? seller.seller_rating.toFixed(1) : '-'}
                          </td>
                          <td className="px-4 py-3 text-sm text-green-600 font-medium">
                            {formatPrice(seller.price)}
                          </td>
                          <td className="px-4 py-3 text-sm">
                            {seller.is_authorized ? (
                              <span className="bg-green-100 text-green-700 px-2 py-1 rounded text-xs">Yetkili</span>
                            ) : (
                              <span className="text-gray-400">-</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-gray-500">Diger satici bulunamadi.</p>
              )}
            </div>
          )}

          {activeTab === 'reviews' && (
            <div>
              {product.reviews && product.reviews.length > 0 ? (
                <div className="space-y-4">
                  {product.reviews.map((review, i) => (
                    <div key={i} className="border-b pb-4 last:border-b-0">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-gray-800">{review.author || 'Anonim'}</span>
                          {review.rating && (
                            <span className="text-yellow-500">
                              {'★'.repeat(review.rating)}{'☆'.repeat(5 - review.rating)}
                            </span>
                          )}
                        </div>
                        {review.review_date && (
                          <span className="text-sm text-gray-400">{review.review_date}</span>
                        )}
                      </div>
                      {review.review_text && (
                        <p className="text-gray-600 text-sm">{review.review_text}</p>
                      )}
                      {review.seller_name && (
                        <p className="text-xs text-gray-400 mt-1">Satici: {review.seller_name}</p>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-500">Yorum bulunamadi.</p>
              )}
            </div>
          )}
        </div>
      </div>

      {snapshots.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-bold text-gray-800 mb-4">Fiyat Gecmisi</h2>
            <Plot
              data={[priceData]}
              layout={{
                autosize: true,
                height: 300,
                margin: { l: 50, r: 20, t: 20, b: 50 },
                xaxis: { title: 'Tarih' },
                yaxis: { title: 'Fiyat (TL)' }
              }}
              config={{ responsive: true }}
              style={{ width: '100%' }}
            />
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-bold text-gray-800 mb-4">Puan Gecmisi</h2>
            <Plot
              data={[ratingData]}
              layout={{
                autosize: true,
                height: 300,
                margin: { l: 50, r: 20, t: 20, b: 50 },
                xaxis: { title: 'Tarih' },
                yaxis: { title: 'Puan', range: [0, 5] }
              }}
              config={{ responsive: true }}
              style={{ width: '100%' }}
            />
          </div>
        </div>
      )}

      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-bold text-gray-800 mb-4">AI Analiz</h2>
        <div className="flex gap-4 mb-4">
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ozel bir soru sorun (opsiyonel)..."
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
          <button
            onClick={handleAnalyze}
            disabled={analyzing}
            className="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
          >
            {analyzing ? 'Analiz Ediliyor...' : 'Analiz Et'}
          </button>
        </div>
        {analysis && (
          <div className="bg-gray-50 rounded-lg p-4 whitespace-pre-wrap">
            {analysis}
          </div>
        )}
      </div>
    </div>
  );
}
