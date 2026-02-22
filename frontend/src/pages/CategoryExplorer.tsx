import { useState, useEffect, useCallback, useMemo } from 'react';
import { createPortal } from 'react-dom';
import {
  scrapeCategoryPage,
  getCategorySessions,
  deleteCategorySession,
  fetchCategoryProductDetail,
  bulkFetchCategoryDetails,
  getCategoryFetchStatus,
  getCategoryProductDetail,
} from '../services/api';

interface CategoryProduct {
  id: number;
  session_id: string;
  name: string;
  url: string;
  image_url: string;
  brand: string;
  price: number | null;
  original_price: number | null;
  discount_percentage: number | null;
  rating: number | null;
  review_count: number | null;
  is_sponsored: boolean;
  campaign_text: string;
  seller_name: string;
  page_number: number;
  position: number;
  detail_fetched: boolean;
  detail_data: any;
}

interface Breadcrumb {
  name: string;
  url: string;
}

interface SessionInfo {
  id: string;
  platform: string;
  category_url: string;
  category_name: string;
  breadcrumbs: Breadcrumb[];
  total_products: number;
  pages_scraped: number;
  product_count: number;
  created_at: string;
}

export default function CategoryExplorer() {
  const [categoryUrl, setCategoryUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [session, setSession] = useState<SessionInfo | null>(null);
  const [products, setProducts] = useState<CategoryProduct[]>([]);
  const [breadcrumbs, setBreadcrumbs] = useState<Breadcrumb[]>([]);
  const [hasNextPage, setHasNextPage] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [selectedProduct, setSelectedProduct] = useState<CategoryProduct | null>(null);
  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [showSessions, setShowSessions] = useState(false);
  const [fetchingDetail, setFetchingDetail] = useState<Set<number>>(new Set());
  const [bulkFetching, setBulkFetching] = useState(false);
  const [fetchStatus, setFetchStatus] = useState<{total_products: number; detail_fetched: number; pending: number} | null>(null);

  const [brandFilter, setBrandFilter] = useState('');
  const [sponsoredFilter, setSponsoredFilter] = useState<'all' | 'sponsored' | 'organic'>('all');
  const [minPrice, setMinPrice] = useState('');
  const [maxPrice, setMaxPrice] = useState('');
  const [searchFilter, setSearchFilter] = useState('');
  const [showFilters, setShowFilters] = useState(false);

  const handleScrape = async (url?: string, page?: number, sessionId?: string) => {
    const targetUrl = url || categoryUrl;
    if (!targetUrl) return;

    setLoading(true);
    setMessage('');
    try {
      const data = await scrapeCategoryPage(targetUrl, page || 1, sessionId || session?.id);
      setSession(data.session);
      setProducts(data.products);
      setBreadcrumbs(data.breadcrumbs || data.session?.breadcrumbs || []);
      setHasNextPage(data.has_next_page);
      setCurrentPage(page || 1);
      setMessage(`Page ${page || 1} scraped: ${data.products_found} products found, ${data.products_added} new added. Total: ${data.total_in_session}`);
      if (!url) setCategoryUrl(targetUrl);
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || 'Failed to scrape category page');
    } finally {
      setLoading(false);
    }
  };

  const handleLoadMore = async () => {
    if (!session) return;
    const nextPage = currentPage + 1;
    await handleScrape(session.category_url, nextPage, session.id);
  };

  const handleBreadcrumbClick = (bc: Breadcrumb) => {
    setCategoryUrl(bc.url);
    setSession(null);
    setProducts([]);
    setBreadcrumbs([]);
    setCurrentPage(1);
    handleScrape(bc.url, 1);
  };

  const handleFetchDetail = async (productId: number) => {
    setFetchingDetail(prev => new Set(prev).add(productId));
    try {
      await fetchCategoryProductDetail([productId]);
      setTimeout(async () => {
        try {
          const detail = await getCategoryProductDetail(productId);
          setProducts(prev => prev.map(p => p.id === productId ? { ...p, detail_fetched: detail.detail_fetched, detail_data: detail.detail_data } : p));
          if (selectedProduct?.id === productId) {
            setSelectedProduct({ ...selectedProduct, detail_fetched: detail.detail_fetched, detail_data: detail.detail_data });
          }
        } catch {}
        setFetchingDetail(prev => {
          const next = new Set(prev);
          next.delete(productId);
          return next;
        });
      }, 5000);
    } catch {
      setFetchingDetail(prev => {
        const next = new Set(prev);
        next.delete(productId);
        return next;
      });
    }
  };

  const handleBulkFetch = async () => {
    if (!session) return;
    setBulkFetching(true);
    setMessage('');
    try {
      const filteredIds = filteredProducts.filter(p => !p.detail_fetched).map(p => p.id);
      const data = await bulkFetchCategoryDetails(session.id, filteredIds.length > 0 ? filteredIds : undefined);
      setMessage(data.message);
      pollFetchStatus();
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || 'Bulk fetch failed');
      setBulkFetching(false);
    }
  };

  const pollFetchStatus = useCallback(async () => {
    if (!session) return;
    try {
      const status = await getCategoryFetchStatus(session.id);
      setFetchStatus(status);
      if (status.pending > 0) {
        setTimeout(pollFetchStatus, 3000);
      } else {
        setBulkFetching(false);
        setMessage(`All ${status.detail_fetched} product details fetched`);
        const sessionData = await scrapeCategoryPage(session.category_url, 1, session.id);
        setProducts(sessionData.products);
      }
    } catch {
      setBulkFetching(false);
    }
  }, [session]);

  const loadSessions = async () => {
    try {
      const data = await getCategorySessions();
      setSessions(data.sessions);
    } catch {}
  };

  const handleDeleteSession = async (sessionId: string) => {
    try {
      await deleteCategorySession(sessionId);
      setSessions(prev => prev.filter(s => s.id !== sessionId));
      if (session?.id === sessionId) {
        setSession(null);
        setProducts([]);
        setBreadcrumbs([]);
      }
    } catch {}
  };

  const handleLoadSession = async (s: SessionInfo) => {
    setCategoryUrl(s.category_url);
    setSession(s);
    setBreadcrumbs(s.breadcrumbs || []);
    setShowSessions(false);
    await handleScrape(s.category_url, 1, s.id);
  };

  const brands = useMemo(() => {
    const set = new Set<string>();
    products.forEach(p => { if (p.brand) set.add(p.brand); });
    return Array.from(set).sort();
  }, [products]);

  const filteredProducts = useMemo(() => {
    return products.filter(p => {
      if (brandFilter && p.brand !== brandFilter) return false;
      if (sponsoredFilter === 'sponsored' && !p.is_sponsored) return false;
      if (sponsoredFilter === 'organic' && p.is_sponsored) return false;
      if (minPrice && p.price && p.price < parseFloat(minPrice)) return false;
      if (maxPrice && p.price && p.price > parseFloat(maxPrice)) return false;
      if (searchFilter) {
        const q = searchFilter.toLowerCase();
        const nameMatch = p.name?.toLowerCase().includes(q);
        const brandMatch = p.brand?.toLowerCase().includes(q);
        if (!nameMatch && !brandMatch) return false;
      }
      return true;
    });
  }, [products, brandFilter, sponsoredFilter, minPrice, maxPrice, searchFilter]);

  const stats = useMemo(() => {
    const total = filteredProducts.length;
    const sponsored = filteredProducts.filter(p => p.is_sponsored).length;
    const withPrice = filteredProducts.filter(p => p.price).length;
    const avgPrice = withPrice > 0
      ? filteredProducts.reduce((sum, p) => sum + (p.price || 0), 0) / withPrice
      : 0;
    const fetched = filteredProducts.filter(p => p.detail_fetched).length;
    return { total, sponsored, withPrice, avgPrice, fetched };
  }, [filteredProducts]);

  const formatPrice = (price: number | null) => {
    if (!price) return '-';
    return new Intl.NumberFormat('tr-TR', { style: 'currency', currency: 'TRY', minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(price);
  };

  const detectedPlatform = useMemo(() => {
    if (categoryUrl.includes('hepsiburada.com')) return 'hepsiburada';
    if (categoryUrl.includes('trendyol.com')) return 'trendyol';
    return null;
  }, [categoryUrl]);

  return (
    <div className="space-y-6 pb-10">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-xs text-neutral-500 uppercase tracking-wider mb-1">Competitive Analysis</div>
          <h1 className="text-2xl font-bold text-white">Category Explorer</h1>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => { setShowSessions(!showSessions); if (!showSessions) loadSessions(); }}
            className="px-3 py-2 text-sm rounded-lg border border-white/10 text-neutral-300 hover:bg-white/5 transition-colors flex items-center gap-1.5"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            History
          </button>
        </div>
      </div>

      <div className="rounded-xl border border-white/10 p-5" style={{ background: 'linear-gradient(135deg, rgba(0,212,255,0.05), rgba(0,212,255,0.02))' }}>
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="flex-1 relative">
            <input
              type="text"
              value={categoryUrl}
              onChange={(e) => setCategoryUrl(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && !loading) { setSession(null); setProducts([]); handleScrape(); } }}
              placeholder="Paste category URL — e.g. https://www.hepsiburada.com/hizli-cilalar-c-20035738"
              className="w-full bg-black/30 border border-white/10 rounded-lg px-4 py-3 text-sm text-neutral-200 placeholder:text-neutral-600 focus:outline-none focus:border-cyan-500/50 pr-20"
            />
            {detectedPlatform && (
              <span className={`absolute right-3 top-1/2 -translate-y-1/2 text-xs px-2 py-0.5 rounded-full font-medium ${
                detectedPlatform === 'hepsiburada' ? 'bg-orange-500/20 text-orange-400' : 'bg-purple-500/20 text-purple-400'
              }`}>
                {detectedPlatform === 'hepsiburada' ? 'HB' : 'TY'}
              </span>
            )}
          </div>
          <button
            onClick={() => { setSession(null); setProducts([]); setBreadcrumbs([]); setCurrentPage(1); handleScrape(); }}
            disabled={loading || !categoryUrl}
            className="px-6 py-3 text-sm rounded-lg text-white font-medium disabled:opacity-50 flex items-center gap-2 whitespace-nowrap"
            style={{ background: 'linear-gradient(135deg, #00d4ff, #0099cc)' }}
          >
            {loading ? (
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            )}
            Explore Category
          </button>
        </div>
        <div className="mt-2 flex gap-3 text-xs text-neutral-500">
          <span>Hepsiburada: /kategori-adi-c-XXXX</span>
          <span>|</span>
          <span>Trendyol: /sr?q=... or /kategori-adi</span>
        </div>
      </div>

      {showSessions && sessions.length > 0 && (
        <div className="rounded-xl border border-white/10 p-4" style={{ background: 'linear-gradient(180deg, #141619 0%, #0e0f11 100%)' }}>
          <h3 className="text-sm font-medium text-white mb-3">Recent Sessions</h3>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {sessions.map(s => (
              <div key={s.id} className="flex items-center justify-between p-2 rounded-lg hover:bg-white/5 group">
                <button onClick={() => handleLoadSession(s)} className="flex-1 text-left">
                  <span className={`text-xs px-1.5 py-0.5 rounded mr-2 ${s.platform === 'hepsiburada' ? 'bg-orange-500/20 text-orange-400' : 'bg-purple-500/20 text-purple-400'}`}>
                    {s.platform === 'hepsiburada' ? 'HB' : 'TY'}
                  </span>
                  <span className="text-sm text-neutral-300">{s.category_name || 'Unnamed'}</span>
                  <span className="text-xs text-neutral-500 ml-2">{s.product_count} products, {s.pages_scraped} pages</span>
                </button>
                <button onClick={() => handleDeleteSession(s.id)} className="p-1 opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-300">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {message && (
        <div className={`text-sm px-4 py-2.5 rounded-lg border ${message.includes('fail') || message.includes('Failed') ? 'border-red-500/30 bg-red-500/10 text-red-300' : 'border-cyan-500/20 bg-cyan-500/5 text-cyan-300'}`}>
          {message}
        </div>
      )}

      {breadcrumbs.length > 0 && (
        <div className="flex items-center gap-1.5 text-sm flex-wrap">
          {breadcrumbs.map((bc, i) => (
            <span key={i} className="flex items-center gap-1.5">
              {i > 0 && <svg className="w-3 h-3 text-neutral-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" /></svg>}
              <button
                onClick={() => handleBreadcrumbClick(bc)}
                className={`hover:text-cyan-400 transition-colors ${i === breadcrumbs.length - 1 ? 'text-white font-medium' : 'text-neutral-400'}`}
              >
                {bc.name}
              </button>
            </span>
          ))}
          {session && (
            <span className="ml-2 text-xs text-neutral-500">
              ({session.total_products > 0 ? `${session.total_products.toLocaleString()} products` : `${products.length} loaded`})
            </span>
          )}
        </div>
      )}

      {products.length > 0 && (
        <>
          <div className="flex flex-wrap items-center gap-2">
            <button onClick={() => setShowFilters(!showFilters)} className="px-3 py-2 text-sm rounded-lg border border-white/10 text-neutral-300 hover:bg-white/5 flex items-center gap-1.5">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" /></svg>
              Filters
            </button>

            <input
              type="text"
              value={searchFilter}
              onChange={(e) => setSearchFilter(e.target.value)}
              placeholder="Search products..."
              className="bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-neutral-200 placeholder:text-neutral-600 focus:outline-none focus:border-cyan-500/50 w-48"
            />

            <div className="flex-1" />

            <button
              onClick={handleBulkFetch}
              disabled={bulkFetching}
              className="px-3 py-2 text-sm rounded-lg border border-cyan-500/30 text-cyan-400 hover:bg-cyan-500/10 flex items-center gap-1.5 disabled:opacity-50"
            >
              {bulkFetching ? (
                <div className="w-3.5 h-3.5 border-2 border-cyan-400/30 border-t-cyan-400 rounded-full animate-spin" />
              ) : (
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
              )}
              Bulk Fetch Details {fetchStatus && bulkFetching ? `(${fetchStatus.detail_fetched}/${fetchStatus.total_products})` : ''}
            </button>

            {hasNextPage && (
              <button
                onClick={handleLoadMore}
                disabled={loading}
                className="px-3 py-2 text-sm rounded-lg text-white font-medium disabled:opacity-50 flex items-center gap-1.5"
                style={{ background: 'linear-gradient(135deg, #00d4ff, #0099cc)' }}
              >
                {loading ? (
                  <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" /></svg>
                )}
                Load Page {currentPage + 1}
              </button>
            )}
          </div>

          {showFilters && (
            <div className="rounded-xl border border-white/10 p-4 grid grid-cols-2 md:grid-cols-4 gap-3" style={{ background: 'linear-gradient(180deg, #141619 0%, #0e0f11 100%)' }}>
              <div>
                <label className="text-xs text-neutral-500 block mb-1">Brand</label>
                <select value={brandFilter} onChange={(e) => setBrandFilter(e.target.value)} className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-sm text-neutral-200">
                  <option value="">All Brands</option>
                  {brands.map(b => <option key={b} value={b}>{b}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs text-neutral-500 block mb-1">Type</label>
                <select value={sponsoredFilter} onChange={(e) => setSponsoredFilter(e.target.value as any)} className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-sm text-neutral-200">
                  <option value="all">All</option>
                  <option value="organic">Organic Only</option>
                  <option value="sponsored">Sponsored Only</option>
                </select>
              </div>
              <div>
                <label className="text-xs text-neutral-500 block mb-1">Min Price</label>
                <input type="number" value={minPrice} onChange={(e) => setMinPrice(e.target.value)} placeholder="0" className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-sm text-neutral-200" />
              </div>
              <div>
                <label className="text-xs text-neutral-500 block mb-1">Max Price</label>
                <input type="number" value={maxPrice} onChange={(e) => setMaxPrice(e.target.value)} placeholder="999999" className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-sm text-neutral-200" />
              </div>
            </div>
          )}

          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-1.5 text-center">
            <div className="rounded-lg border border-white/5 p-3" style={{ background: 'rgba(255,255,255,0.02)' }}>
              <div className="text-lg font-bold text-white">{stats.total}</div>
              <div className="text-xs text-neutral-500">Showing</div>
            </div>
            <div className="rounded-lg border border-white/5 p-3" style={{ background: 'rgba(255,255,255,0.02)' }}>
              <div className="text-lg font-bold text-cyan-400">{formatPrice(stats.avgPrice)}</div>
              <div className="text-xs text-neutral-500">Avg Price</div>
            </div>
            <div className="rounded-lg border border-white/5 p-3" style={{ background: 'rgba(255,255,255,0.02)' }}>
              <div className="text-lg font-bold text-amber-400">{stats.sponsored}</div>
              <div className="text-xs text-neutral-500">Sponsored</div>
            </div>
            <div className="rounded-lg border border-white/5 p-3" style={{ background: 'rgba(255,255,255,0.02)' }}>
              <div className="text-lg font-bold text-emerald-400">{stats.fetched}/{stats.total}</div>
              <div className="text-xs text-neutral-500">Details Fetched</div>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {filteredProducts.map((product, idx) => (
              <div
                key={product.id}
                className="rounded-xl border border-white/10 overflow-hidden hover:border-white/20 transition-all cursor-pointer group relative"
                style={{ background: 'linear-gradient(180deg, #141619 0%, #0e0f11 100%)' }}
                onClick={() => setSelectedProduct(product)}
              >
                {product.is_sponsored && (
                  <div className="absolute top-2 left-2 z-10">
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-400 font-medium">AD</span>
                  </div>
                )}

                <div className="absolute top-2 right-2 z-10 flex items-center gap-1">
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/10 text-neutral-400">#{product.position}</span>
                  <button
                    onClick={(e) => { e.stopPropagation(); handleFetchDetail(product.id); }}
                    disabled={fetchingDetail.has(product.id) || product.detail_fetched}
                    className={`p-1 rounded transition-colors ${product.detail_fetched ? 'bg-emerald-500/20 text-emerald-400' : 'bg-white/10 text-neutral-400 hover:bg-cyan-500/20 hover:text-cyan-400'} disabled:opacity-50`}
                    title={product.detail_fetched ? 'Detail fetched' : 'Fetch product detail'}
                  >
                    {fetchingDetail.has(product.id) ? (
                      <div className="w-3.5 h-3.5 border-2 border-cyan-400/30 border-t-cyan-400 rounded-full animate-spin" />
                    ) : product.detail_fetched ? (
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
                    ) : (
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
                    )}
                  </button>
                </div>

                <div className="aspect-square bg-white/5 flex items-center justify-center p-2 overflow-hidden">
                  {product.image_url ? (
                    <img src={product.image_url} alt={product.name} className="max-h-full max-w-full object-contain" loading="lazy" />
                  ) : (
                    <svg className="w-12 h-12 text-neutral-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                  )}
                </div>

                <div className="p-3">
                  {product.brand && (
                    <div className="text-[11px] font-medium text-cyan-400 mb-1 truncate uppercase">{product.brand}</div>
                  )}
                  <h3 className="text-sm text-neutral-200 line-clamp-2 leading-snug mb-2 min-h-[2.5rem]">{product.name || 'Unnamed Product'}</h3>

                  <div className="flex items-end justify-between">
                    <div>
                      {product.price ? (
                        <>
                          <div className="text-base font-bold text-white">{formatPrice(product.price)}</div>
                          {product.original_price && product.original_price > product.price && (
                            <div className="flex items-center gap-1.5">
                              <span className="text-xs text-neutral-500 line-through">{formatPrice(product.original_price)}</span>
                              <span className="text-[10px] text-red-400 font-medium">-{product.discount_percentage}%</span>
                            </div>
                          )}
                        </>
                      ) : (
                        <div className="text-sm text-neutral-500">-</div>
                      )}
                    </div>
                    {product.rating && (
                      <div className="text-right">
                        <div className="flex items-center gap-0.5 text-amber-400">
                          <svg className="w-3 h-3 fill-current" viewBox="0 0 20 20"><path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" /></svg>
                          <span className="text-xs">{product.rating}</span>
                        </div>
                        {product.review_count != null && (
                          <div className="text-[10px] text-neutral-500">{product.review_count.toLocaleString()}</div>
                        )}
                      </div>
                    )}
                  </div>

                  {product.campaign_text && (
                    <div className="mt-2 text-[10px] text-orange-400 bg-orange-500/10 rounded px-1.5 py-0.5 truncate">{product.campaign_text}</div>
                  )}
                </div>
              </div>
            ))}
          </div>

          {hasNextPage && (
            <div className="flex justify-center pt-4">
              <button
                onClick={handleLoadMore}
                disabled={loading}
                className="px-8 py-3 text-sm rounded-xl text-white font-medium disabled:opacity-50 flex items-center gap-2"
                style={{ background: 'linear-gradient(135deg, #00d4ff, #0099cc)' }}
              >
                {loading ? (
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" /></svg>
                )}
                Load More — Page {currentPage + 1}
              </button>
            </div>
          )}
        </>
      )}

      {!products.length && !loading && !message && (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div className="w-16 h-16 rounded-2xl bg-white/5 flex items-center justify-center mb-4">
            <svg className="w-8 h-8 text-neutral-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-neutral-300 mb-2">Explore Marketplace Categories</h3>
          <p className="text-sm text-neutral-500 max-w-md">
            Paste a Hepsiburada or Trendyol category URL above to browse products, analyze competitors, check SEO positioning, and review pricing strategies.
          </p>
        </div>
      )}

      {selectedProduct && createPortal(
        <>
          <div className="fixed inset-0 bg-black/60 z-[9998]" onClick={() => setSelectedProduct(null)} />
          <div
            className="fixed top-0 right-0 h-full w-full max-w-lg z-[9999] overflow-y-auto border-l border-white/10 shadow-2xl"
            style={{ background: 'linear-gradient(180deg, #141619 0%, #0e0f11 100%)' }}
            onClick={(e) => e.stopPropagation()}
            onKeyDown={(e) => { if (e.key === 'Escape') setSelectedProduct(null); }}
            tabIndex={-1}
            ref={(el) => el?.focus()}
          >
            <div className="sticky top-0 z-10 flex items-center justify-between p-4 border-b border-white/10" style={{ background: 'rgba(20,22,25,0.95)', backdropFilter: 'blur(8px)' }}>
              <h3 className="text-base font-semibold text-white truncate pr-4">Product Details</h3>
              <div className="flex items-center gap-2">
                {!selectedProduct.detail_fetched && (
                  <button
                    onClick={() => handleFetchDetail(selectedProduct.id)}
                    disabled={fetchingDetail.has(selectedProduct.id)}
                    className="px-3 py-1.5 text-xs rounded-lg border border-cyan-500/30 text-cyan-400 hover:bg-cyan-500/10 flex items-center gap-1"
                  >
                    {fetchingDetail.has(selectedProduct.id) ? (
                      <div className="w-3 h-3 border-2 border-cyan-400/30 border-t-cyan-400 rounded-full animate-spin" />
                    ) : (
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
                    )}
                    Fetch Detail
                  </button>
                )}
                <a href={selectedProduct.url} target="_blank" rel="noopener noreferrer" className="p-1.5 rounded-lg hover:bg-white/10 text-neutral-400">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
                </a>
                <button onClick={() => setSelectedProduct(null)} className="p-1.5 rounded-lg hover:bg-white/10 text-neutral-400">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
                </button>
              </div>
            </div>

            <div className="p-4 space-y-4">
              {selectedProduct.image_url && (
                <div className="rounded-lg bg-white/5 p-4 flex items-center justify-center">
                  <img src={selectedProduct.image_url} alt={selectedProduct.name} className="max-h-64 object-contain" />
                </div>
              )}

              <div>
                {selectedProduct.brand && <div className="text-xs text-cyan-400 font-medium uppercase mb-1">{selectedProduct.brand}</div>}
                <h4 className="text-base font-medium text-white leading-snug">{selectedProduct.name}</h4>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-lg bg-white/5 p-3">
                  <div className="text-xs text-neutral-500 mb-1">Price</div>
                  <div className="text-lg font-bold text-white">{formatPrice(selectedProduct.price)}</div>
                  {selectedProduct.original_price && selectedProduct.original_price > (selectedProduct.price || 0) && (
                    <div className="text-xs text-neutral-500 line-through">{formatPrice(selectedProduct.original_price)}</div>
                  )}
                </div>
                <div className="rounded-lg bg-white/5 p-3">
                  <div className="text-xs text-neutral-500 mb-1">Rating</div>
                  <div className="text-lg font-bold text-white">{selectedProduct.rating || '-'}</div>
                  <div className="text-xs text-neutral-500">{selectedProduct.review_count?.toLocaleString() || '0'} reviews</div>
                </div>
              </div>

              <div className="space-y-2 text-sm">
                <div className="flex justify-between py-1.5 border-b border-white/5">
                  <span className="text-neutral-500">Position</span>
                  <span className="text-white">#{selectedProduct.position}</span>
                </div>
                <div className="flex justify-between py-1.5 border-b border-white/5">
                  <span className="text-neutral-500">Page</span>
                  <span className="text-white">{selectedProduct.page_number}</span>
                </div>
                <div className="flex justify-between py-1.5 border-b border-white/5">
                  <span className="text-neutral-500">Sponsored</span>
                  <span className={selectedProduct.is_sponsored ? 'text-amber-400' : 'text-neutral-400'}>{selectedProduct.is_sponsored ? 'Yes' : 'No'}</span>
                </div>
                {selectedProduct.seller_name && (
                  <div className="flex justify-between py-1.5 border-b border-white/5">
                    <span className="text-neutral-500">Seller</span>
                    <span className="text-white">{selectedProduct.seller_name}</span>
                  </div>
                )}
                {selectedProduct.campaign_text && (
                  <div className="flex justify-between py-1.5 border-b border-white/5">
                    <span className="text-neutral-500">Campaign</span>
                    <span className="text-orange-400 text-xs">{selectedProduct.campaign_text}</span>
                  </div>
                )}
              </div>

              {selectedProduct.detail_fetched && selectedProduct.detail_data && (
                <div className="space-y-3 pt-2">
                  <h5 className="text-sm font-medium text-white border-b border-white/10 pb-2">Fetched Details</h5>

                  {selectedProduct.detail_data.description && (
                    <div>
                      <div className="text-xs text-neutral-500 mb-1">Description</div>
                      <p className="text-xs text-neutral-300 leading-relaxed max-h-32 overflow-y-auto">{selectedProduct.detail_data.description}</p>
                    </div>
                  )}

                  {selectedProduct.detail_data.category_breadcrumbs && (
                    <div>
                      <div className="text-xs text-neutral-500 mb-1">Category</div>
                      <p className="text-xs text-neutral-300">
                        {Array.isArray(selectedProduct.detail_data.category_breadcrumbs)
                          ? selectedProduct.detail_data.category_breadcrumbs.map((c: any) => typeof c === 'string' ? c : c.name).join(' > ')
                          : selectedProduct.detail_data.category}
                      </p>
                    </div>
                  )}

                  {selectedProduct.detail_data.product_specs && Object.keys(selectedProduct.detail_data.product_specs).length > 0 && (
                    <div>
                      <div className="text-xs text-neutral-500 mb-1">Specifications</div>
                      <div className="space-y-1">
                        {Object.entries(selectedProduct.detail_data.product_specs).slice(0, 10).map(([k, v]) => (
                          <div key={k} className="flex justify-between text-xs py-0.5">
                            <span className="text-neutral-500">{k}</span>
                            <span className="text-neutral-300">{String(v)}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {selectedProduct.detail_data.reviews && selectedProduct.detail_data.reviews.length > 0 && (
                    <div>
                      <div className="text-xs text-neutral-500 mb-1">Reviews ({selectedProduct.detail_data.reviews.length})</div>
                      <div className="space-y-2 max-h-48 overflow-y-auto">
                        {selectedProduct.detail_data.reviews.slice(0, 5).map((r: any, i: number) => (
                          <div key={i} className="rounded-lg bg-white/5 p-2 text-xs">
                            <div className="flex items-center gap-1 mb-1">
                              {r.rating && <span className="text-amber-400">{r.rating}★</span>}
                              {r.author && <span className="text-neutral-400">{r.author}</span>}
                            </div>
                            <p className="text-neutral-300 line-clamp-3">{r.text || r.body || r.content}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {!selectedProduct.detail_fetched && (
                <div className="rounded-lg bg-white/5 p-4 text-center">
                  <p className="text-xs text-neutral-500 mb-2">Click "Fetch Detail" to load full product data including description, specs, reviews, and more.</p>
                  <button
                    onClick={() => handleFetchDetail(selectedProduct.id)}
                    disabled={fetchingDetail.has(selectedProduct.id)}
                    className="px-4 py-2 text-sm rounded-lg text-white font-medium disabled:opacity-50"
                    style={{ background: 'linear-gradient(135deg, #00d4ff, #0099cc)' }}
                  >
                    Fetch Full Details
                  </button>
                </div>
              )}
            </div>
          </div>
        </>,
        document.body
      )}
    </div>
  );
}
