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
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
      <div className="card-dark p-12 text-center">
        <div className="w-10 h-10 border-2 border-accent-primary/30 border-t-accent-primary rounded-full animate-spin mx-auto" />
        <p className="mt-4 text-text-muted">Loading product...</p>
      </div>
    );
  }

  if (!product) {
    return (
      <div className="card-dark p-12 text-center">
        <div className="w-12 h-12 rounded-full bg-surface-hover flex items-center justify-center mx-auto mb-4">
          <svg className="w-6 h-6 text-neutral-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <p className="text-text-muted">Product not found</p>
      </div>
    );
  }

  const priceData = {
    x: snapshots.map(s => s.snapshot_date),
    y: snapshots.map(s => s.price || 0),
    type: 'scatter' as const,
    mode: 'lines+markers' as const,
    name: 'Price',
    line: { color: '#1e9df1', width: 2 },
    marker: { color: '#1e9df1', size: 6 }
  };

  const ratingData = {
    x: snapshots.map(s => s.snapshot_date),
    y: snapshots.map(s => s.rating || 0),
    type: 'scatter' as const,
    mode: 'lines+markers' as const,
    name: 'Rating',
    line: { color: '#22c55e', width: 2 },
    marker: { color: '#22c55e', size: 6 }
  };

  const isDark = document.documentElement.classList.contains('dark');

  const plotLayout = {
    paper_bgcolor: isDark ? '#1C2E28' : 'transparent',
    plot_bgcolor: isDark ? '#1C2E28' : 'transparent',
    font: { color: isDark ? '#A7C4B8' : '#9e8b66' },
    xaxis: {
      gridcolor: isDark ? 'rgba(74,222,128,0.08)' : 'rgba(91,72,36,0.08)',
      linecolor: isDark ? 'rgba(74,222,128,0.12)' : 'rgba(91,72,36,0.12)'
    },
    yaxis: {
      gridcolor: isDark ? 'rgba(74,222,128,0.08)' : 'rgba(91,72,36,0.08)',
      linecolor: isDark ? 'rgba(74,222,128,0.12)' : 'rgba(91,72,36,0.12)'
    },
    margin: { l: 50, r: 20, t: 20, b: 50 },
    autosize: true,
    height: 280
  };

  const hasDiscount = product.discounted_price && product.latest_price && product.discounted_price < product.latest_price;

  return (
    <div className="space-y-5 md:space-y-6 animate-fade-in">
      <div className="flex flex-wrap items-center gap-2 text-xs md:text-sm text-neutral-500">
        <Link to="/products" className="hover:text-accent-primary transition-colors">Products</Link>
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
        <span className="text-text-body">Detail</span>
      </div>

      <div className="card-dark p-4 md:p-6">
        <div className="flex flex-col lg:flex-row gap-4 md:gap-6">
          {product.image_url ? (
            <img src={product.image_url} alt="" className="w-full sm:w-56 md:w-64 lg:w-48 h-56 md:h-64 lg:h-48 object-cover rounded-lg border border-accent-primary/12" />
          ) : (
            <div className="w-full sm:w-56 md:w-64 lg:w-48 h-56 md:h-64 lg:h-48 rounded-lg bg-surface-hover flex items-center justify-center">
              <svg className="w-12 h-12 text-text-faded" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
            </div>
          )}
          <div className="flex-1 min-w-0">
            {product.brand && (
              <span className="badge badge-info mb-2">{product.brand}</span>
            )}
            <h1 className="text-xl md:text-2xl font-bold text-text-primary mb-3 break-words">{product.name}</h1>
            
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-1 text-xs md:text-sm mb-4">
              <p className="text-text-muted">Platform: <span className="text-text-secondary">{product.platform}</span></p>
              {product.seller_name && (
                <p className="text-text-muted">
                  Seller: <span className="text-text-secondary">{product.seller_name}</span>
                  {product.seller_rating && (
                    <span className="ml-2 text-warning">({product.seller_rating.toFixed(1)})</span>
                  )}
                </p>
              )}
              {product.category_hierarchy && <p className="text-text-muted">Category: <span className="text-text-secondary">{product.category_hierarchy}</span></p>}
              {product.origin_country && <p className="text-text-muted">Origin: <span className="text-text-secondary">{product.origin_country}</span></p>}
              {product.sku && <p className="text-text-muted">SKU: <span className="text-text-secondary">{product.sku}</span></p>}
              {product.barcode && <p className="text-text-muted">Barcode: <span className="text-text-secondary">{product.barcode}</span></p>}
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-2 md:gap-3 mb-4">
              <div className="stat-card py-3 px-3 md:px-4" style={{ '--stat-color': '#22c55e' } as React.CSSProperties}>
                {hasDiscount ? (
                  <>
                    <div className="text-sm line-through text-neutral-500">{formatPrice(product.latest_price)}</div>
                    <div className="text-xl font-bold text-success">{formatPrice(product.discounted_price)}</div>
                  </>
                ) : (
                  <div className="text-xl font-bold text-success">{formatPrice(product.latest_price)}</div>
                )}
                <div className="text-xs text-neutral-500">Current Price</div>
              </div>
              <div className="stat-card py-3 px-3 md:px-4" style={{ '--stat-color': '#f59e0b' } as React.CSSProperties}>
                <div className="text-xl font-bold text-warning">
                  {product.latest_rating ? product.latest_rating.toFixed(1) : '-'}
                </div>
                <div className="text-xs text-neutral-500">Rating</div>
              </div>
              <div className="stat-card py-3 px-3 md:px-4" style={{ '--stat-color': '#1e9df1' } as React.CSSProperties}>
                <div className="text-xl font-bold text-accent-primary">{product.reviews_count || 0}</div>
                <div className="text-xs text-neutral-500">Reviews</div>
              </div>
              <div className="stat-card py-3 px-3 md:px-4" style={{ '--stat-color': '#f7b928' } as React.CSSProperties}>
                <div className="text-xl font-bold text-purple-400">
                  {product.stock_count ? (product.stock_count < 50 ? `<${product.stock_count}` : product.stock_count) : (product.in_stock ? 'Yes' : 'No')}
                </div>
                <div className="text-xs text-neutral-500">Stock</div>
              </div>
            </div>

            {(product.coupons && product.coupons.length > 0) && (
              <div className="mb-3">
                <h3 className="text-sm font-medium text-text-muted mb-2">Coupons</h3>
                <div className="flex flex-wrap gap-2">
                  {product.coupons.map((coupon, i) => (
                    <span key={i} className="badge badge-danger">
                      {coupon.amount} TL {coupon.min_order && `(min: ${coupon.min_order} TL)`}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {(product.campaigns && product.campaigns.length > 0) && (
              <div className="mb-4">
                <h3 className="text-sm font-medium text-text-muted mb-2">Campaigns</h3>
                <div className="flex flex-wrap gap-2">
                  {product.campaigns.map((campaign, i) => (
                    <span key={i} className="badge badge-warning">
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
              className="btn-primary inline-flex items-center gap-2"
            >
              View on Marketplace
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
            </a>
          </div>
        </div>
      </div>

      <div className="card-dark overflow-hidden">
        <div className="border-b border-accent-primary/8">
          <nav className="flex overflow-x-auto scrollbar-thin">
            <button
              onClick={() => setActiveTab('info')}
              className={`px-4 md:px-6 py-3.5 md:py-4 border-b-2 font-medium text-xs md:text-sm transition-all whitespace-nowrap ${
                activeTab === 'info' ? 'border-accent-primary text-accent-primary' : 'border-transparent text-text-muted hover:text-text-secondary'
              }`}
            >
              Product Info
            </button>
            <button
              onClick={() => setActiveTab('sellers')}
              className={`px-4 md:px-6 py-3.5 md:py-4 border-b-2 font-medium text-xs md:text-sm transition-all whitespace-nowrap ${
                activeTab === 'sellers' ? 'border-accent-primary text-accent-primary' : 'border-transparent text-text-muted hover:text-text-secondary'
              }`}
            >
              Other Sellers ({product.other_sellers?.length || 0})
            </button>
            <button
              onClick={() => setActiveTab('reviews')}
              className={`px-4 md:px-6 py-3.5 md:py-4 border-b-2 font-medium text-xs md:text-sm transition-all whitespace-nowrap ${
                activeTab === 'reviews' ? 'border-accent-primary text-accent-primary' : 'border-transparent text-text-muted hover:text-text-secondary'
              }`}
            >
              Reviews ({product.reviews?.length || 0})
            </button>
          </nav>
        </div>

        <div className="p-4 md:p-6">
          {activeTab === 'info' && (
            <div>
              {product.description ? (
                <p className="text-text-body whitespace-pre-wrap leading-relaxed">{product.description}</p>
              ) : (
                <p className="text-neutral-500">No product description available.</p>
              )}
            </div>
          )}

          {activeTab === 'sellers' && (
            <div>
              {product.other_sellers && product.other_sellers.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="table-dark">
                    <thead>
                      <tr>
                        <th>Seller</th>
                        <th>Rating</th>
                        <th>Price</th>
                        <th>Authorized</th>
                      </tr>
                    </thead>
                    <tbody>
                      {product.other_sellers.map((seller, i) => (
                        <tr key={i}>
                          <td className="text-text-secondary">{seller.seller_name}</td>
                          <td className="text-warning">
                            {seller.seller_rating ? seller.seller_rating.toFixed(1) : '-'}
                          </td>
                          <td className="text-success font-medium">
                            {formatPrice(seller.price)}
                          </td>
                          <td>
                            {seller.is_authorized ? (
                              <span className="badge badge-success">Authorized</span>
                            ) : (
                              <span className="text-text-faded">-</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-neutral-500">No other sellers found.</p>
              )}
            </div>
          )}

          {activeTab === 'reviews' && (
            <div>
              {product.reviews && product.reviews.length > 0 ? (
                <div className="space-y-4">
                  {product.reviews.map((review, i) => (
                    <div key={i} className="border-b border-accent-primary/8 pb-4 last:border-b-0">
                      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-2">
                        <div className="flex items-center gap-3">
                          <span className="font-medium text-text-secondary">{review.author || 'Anonymous'}</span>
                          {review.rating && (
                            <span className="text-warning text-sm">
                              {'★'.repeat(review.rating)}
                              <span className="text-text-faded">{'★'.repeat(5 - review.rating)}</span>
                            </span>
                          )}
                        </div>
                        {review.review_date && (
                          <span className="text-xs text-neutral-500">{review.review_date}</span>
                        )}
                      </div>
                      {review.review_text && (
                        <p className="text-text-muted text-sm">{review.review_text}</p>
                      )}
                      {review.seller_name && (
                        <p className="text-xs text-neutral-500 mt-2">Seller: {review.seller_name}</p>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-neutral-500">No reviews found.</p>
              )}
            </div>
          )}
        </div>
      </div>

      {snapshots.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6">
          <div className="card-dark p-4 md:p-5">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-8 h-8 rounded-lg bg-accent-primary/10 flex items-center justify-center">
                <svg className="w-4 h-4 text-accent-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
                </svg>
              </div>
              <h2 className="text-lg font-semibold text-text-primary">Price History</h2>
            </div>
            <Plot
              data={[priceData]}
              layout={{
                ...plotLayout,
                yaxis: { ...plotLayout.yaxis, title: { text: 'Price (TL)', font: { color: isDark ? '#A7C4B8' : '#9e8b66' } } }
              }}
              config={{ responsive: true, displayModeBar: false }}
              style={{ width: '100%' }}
            />
          </div>
          <div className="card-dark p-4 md:p-5">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-8 h-8 rounded-lg bg-success/10 flex items-center justify-center">
                <svg className="w-4 h-4 text-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
                </svg>
              </div>
              <h2 className="text-lg font-semibold text-text-primary">Rating History</h2>
            </div>
            <Plot
              data={[ratingData]}
              layout={{
                ...plotLayout,
                yaxis: { ...plotLayout.yaxis, title: { text: 'Rating', font: { color: isDark ? '#A7C4B8' : '#9e8b66' } }, range: [0, 5] }
              }}
              config={{ responsive: true, displayModeBar: false }}
              style={{ width: '100%' }}
            />
          </div>
        </div>
      )}

      <div className="card-dark p-4 md:p-5">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-8 h-8 rounded-lg bg-purple-500/10 flex items-center justify-center">
            <svg className="w-4 h-4 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
          </div>
          <h2 className="text-lg font-semibold text-text-primary">AI Analysis</h2>
        </div>
        <div className="flex flex-col md:flex-row gap-3 md:gap-4 mb-4">
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask a custom question (optional)..."
            className="input-dark flex-1"
          />
          <button
            onClick={handleAnalyze}
            disabled={analyzing}
            className="btn-primary w-full md:w-auto flex items-center justify-center"
          >
            {analyzing ? (
              <span className="flex items-center gap-2">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Analyzing...
              </span>
            ) : 'Analyze'}
          </button>
        </div>
        {analysis && (
          <div className="bg-dark-800/50 rounded-lg p-4 text-text-body whitespace-pre-wrap border border-accent-primary/8">
            {analysis}
          </div>
        )}
      </div>
    </div>
  );
}
