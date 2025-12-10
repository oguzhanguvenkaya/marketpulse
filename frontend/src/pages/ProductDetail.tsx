import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import Plot from 'react-plotly.js';
import { getProduct, getProductSnapshots, analyzeProducts } from '../services/api';
import type { Product, Snapshot } from '../services/api';

export default function ProductDetail() {
  const { id } = useParams<{ id: string }>();
  const [product, setProduct] = useState<Product | null>(null);
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysis, setAnalysis] = useState<string | null>(null);
  const [question, setQuestion] = useState('');

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
        <p className="mt-4 text-gray-500">Yükleniyor...</p>
      </div>
    );
  }

  if (!product) {
    return (
      <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
        Ürün bulunamadı
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

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 text-sm text-gray-500">
        <Link to="/products" className="hover:text-indigo-600">Ürünler</Link>
        <span>/</span>
        <span>Detay</span>
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex gap-6">
          {product.image_url && (
            <img src={product.image_url} alt="" className="w-48 h-48 object-cover rounded-lg" />
          )}
          <div className="flex-1">
            <h1 className="text-2xl font-bold text-gray-800 mb-2">{product.name}</h1>
            <div className="space-y-2 text-gray-600">
              <p><span className="font-medium">Platform:</span> {product.platform}</p>
              {product.seller_name && <p><span className="font-medium">Satıcı:</span> {product.seller_name}</p>}
              {product.category_path && <p><span className="font-medium">Kategori:</span> {product.category_path}</p>}
            </div>
            <div className="mt-4 flex gap-4">
              <div className="bg-green-50 px-4 py-2 rounded-lg">
                <div className="text-2xl font-bold text-green-600">{formatPrice(product.latest_price)}</div>
                <div className="text-sm text-gray-500">Güncel Fiyat</div>
              </div>
              <div className="bg-yellow-50 px-4 py-2 rounded-lg">
                <div className="text-2xl font-bold text-yellow-600">
                  {product.latest_rating ? `⭐ ${product.latest_rating.toFixed(1)}` : '-'}
                </div>
                <div className="text-sm text-gray-500">Puan</div>
              </div>
              <div className="bg-blue-50 px-4 py-2 rounded-lg">
                <div className="text-2xl font-bold text-blue-600">{product.reviews_count || 0}</div>
                <div className="text-sm text-gray-500">Yorum</div>
              </div>
            </div>
            <a
              href={product.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-block mt-4 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
            >
              Pazaryerinde Görüntüle →
            </a>
          </div>
        </div>
      </div>

      {snapshots.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-bold text-gray-800 mb-4">💰 Fiyat Geçmişi</h2>
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
            <h2 className="text-lg font-bold text-gray-800 mb-4">⭐ Puan Geçmişi</h2>
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
        <h2 className="text-lg font-bold text-gray-800 mb-4">🤖 AI Analiz</h2>
        <div className="flex gap-4 mb-4">
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Özel bir soru sorun (opsiyonel)..."
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
