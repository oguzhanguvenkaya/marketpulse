import { useState, useEffect, useCallback, useRef } from 'react';
import { toast } from 'sonner';
import { createPortal } from 'react-dom';
import {
  getStoreProducts,
  getStoreProductFilters,
  scrapeFromPriceMonitor,
  getScrapeJobStatus,
  importExcelProducts,
  backfillPrices,
  scrapeFromUrls,
  type StoreProduct,
  type StoreProductFilters,
  type StoreProductListResponse,
  type ScrapeJobStatus,
} from '../services/api';

interface Props {
  platform: string;
  platformLabel: string;
  platformColor: string;
  platformIcon: React.ReactNode;
}

export default function MarketplaceProductList({ platform, platformLabel, platformColor, platformIcon }: Props) {
  const [data, setData] = useState<StoreProductListResponse | null>(null);
  const [filters, setFilters] = useState<StoreProductFilters | null>(null);
  const [loading, setLoading] = useState(true);
  const [scraping, setScraping] = useState(false);
  const [scrapeMessage, setScrapeMessage] = useState('');
  const [scrapeJobId, setScrapeJobId] = useState<string | null>(null);
  const [scrapeProgress, setScrapeProgress] = useState<ScrapeJobStatus | null>(null);
  const [importing, setImporting] = useState(false);
  const [importMessage, setImportMessage] = useState('');
  const [showUrlDialog, setShowUrlDialog] = useState(false);
  const [urlText, setUrlText] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [search, setSearch] = useState('');
  const [selectedBrand, setSelectedBrand] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [minPrice, setMinPrice] = useState('');
  const [maxPrice, setMaxPrice] = useState('');
  const [minRating, setMinRating] = useState('');
  const [skuFilter, setSkuFilter] = useState('');
  const [barcodeFilter, setBarcodeFilter] = useState('');
  const [sortBy, setSortBy] = useState('created_at');
  const [sortDir, setSortDir] = useState('desc');
  const [page, setPage] = useState(1);
  const [pageSize] = useState(50);
  const [showFilters, setShowFilters] = useState(false);
  const [selectedProduct, setSelectedProduct] = useState<StoreProduct | null>(null);

  const fetchProducts = useCallback(async () => {
    setLoading(true);
    try {
      const params: any = {
        platform: platform === 'all' ? undefined : platform,
        page,
        page_size: pageSize,
        sort_by: sortBy,
        sort_dir: sortDir,
      };
      if (search) params.search = search;
      if (selectedBrand) params.brand = selectedBrand;
      if (selectedCategory) params.category = selectedCategory;
      if (minPrice) params.min_price = parseFloat(minPrice);
      if (maxPrice) params.max_price = parseFloat(maxPrice);
      if (minRating) params.min_rating = parseFloat(minRating);
      if (skuFilter) params.sku = skuFilter;
      if (barcodeFilter) params.barcode = barcodeFilter;
      const result = await getStoreProducts(params);
      setData(result);
    } catch (err) {
      console.error('Failed to fetch products:', err);
      toast.error('Failed to load products', { id: 'marketplace-products-error' });
    } finally {
      setLoading(false);
    }
  }, [platform, page, pageSize, sortBy, sortDir, search, selectedBrand, selectedCategory, minPrice, maxPrice, minRating, skuFilter, barcodeFilter]);

  const fetchFilters = useCallback(async () => {
    try {
      const f = await getStoreProductFilters(platform === 'all' ? undefined : platform);
      setFilters(f);
    } catch (err) {
      console.error('Failed to fetch filters:', err);
      toast.error('Failed to load filters', { id: 'marketplace-filters-error' });
    }
  }, [platform]);

  useEffect(() => {
    fetchProducts();
    fetchFilters();
  }, [fetchProducts, fetchFilters]);

  useEffect(() => {
    if (!scrapeJobId) return;
    let cancelled = false;
    let timeoutId: ReturnType<typeof setTimeout>;
    const poll = async () => {
      try {
        const status = await getScrapeJobStatus(scrapeJobId);
        if (cancelled) return;
        setScrapeProgress(status);
        if (status.status === 'completed' || status.status === 'failed' || status.status === 'stopped') {
          setScraping(false);
          setScrapeMessage(
            `Job ${status.status}: ${status.completed} scraped, ${status.failed} failed out of ${status.total} URLs`
          );
          fetchProducts();
          fetchFilters();
          return;
        }
      } catch {
        if (cancelled) return;
      }
      if (!cancelled) {
        timeoutId = setTimeout(poll, 3000);
      }
    };
    timeoutId = setTimeout(poll, 2000);
    return () => { cancelled = true; clearTimeout(timeoutId); };
  }, [scrapeJobId, fetchProducts, fetchFilters]);

  const handleScrape = async () => {
    setScraping(true);
    setScrapeMessage('');
    setScrapeProgress(null);
    setScrapeJobId(null);
    try {
      const result = await scrapeFromPriceMonitor(platform === 'all' ? undefined : platform);
      setScrapeJobId(result.job_id);
      setScrapeMessage(`Scraping started — ${result.total_urls} URLs queued`);
    } catch (err: any) {
      setScrapeMessage(err?.response?.data?.detail || 'Scraping failed');
      setScraping(false);
    }
  };

  const handleExcelImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setImporting(true);
    setImportMessage('');
    try {
      const result = await importExcelProducts(file);
      setImportMessage(`Imported: ${result.created} new, ${result.updated} updated, ${result.skipped} skipped`);
      fetchProducts();
      fetchFilters();
    } catch (err: any) {
      setImportMessage(err?.response?.data?.detail || 'Import failed');
    } finally {
      setImporting(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleUrlScrape = async () => {
    const urls = urlText.split('\n').map(u => u.trim()).filter(u => u && (u.startsWith('http://') || u.startsWith('https://')));
    if (urls.length === 0) {
      setScrapeMessage('No valid URLs found. Each URL should start with http:// or https://');
      return;
    }
    setScraping(true);
    setScrapeMessage('');
    setScrapeProgress(null);
    setScrapeJobId(null);
    setShowUrlDialog(false);
    setUrlText('');
    try {
      const result = await scrapeFromUrls(urls);
      setScrapeJobId(result.job_id);
      setScrapeMessage(`Scraping started — ${result.total_urls} URLs queued`);
    } catch (err: any) {
      setScrapeMessage(err?.response?.data?.detail || 'URL scraping failed');
      setScraping(false);
    }
  };

  const handleBackfillPrices = async () => {
    setScrapeMessage('Backfilling prices from Price Monitor...');
    try {
      const result = await backfillPrices(platform === 'all' ? undefined : platform);
      setScrapeMessage(result.message);
      if (result.updated > 0) {
        fetchProducts();
      }
    } catch (err: any) {
      setScrapeMessage(err?.response?.data?.detail || 'Backfill failed');
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchProducts();
  };

  const clearFilters = () => {
    setSearch('');
    setSelectedBrand('');
    setSelectedCategory('');
    setMinPrice('');
    setMaxPrice('');
    setMinRating('');
    setSkuFilter('');
    setBarcodeFilter('');
    setPage(1);
  };

  const renderStars = (rating: number) => {
    const full = Math.floor(rating);
    const half = rating - full >= 0.5;
    return (
      <div className="flex items-center gap-0.5">
        {[...Array(5)].map((_, i) => (
          <svg key={i} className={`w-3.5 h-3.5 ${i < full ? 'text-yellow-600 dark:text-yellow-400' : i === full && half ? 'text-yellow-600 dark:text-yellow-400' : 'text-neutral-600'}`} fill="currentColor" viewBox="0 0 20 20">
            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
          </svg>
        ))}
        <span className="ml-1 text-xs text-text-muted">{rating}</span>
      </div>
    );
  };

  const formatPrice = (price: number | null, currency?: string | null) => {
    if (price === null || price === undefined) return '-';
    const sym = currency === 'TRY' ? '₺' : currency === 'USD' ? '$' : currency === 'EUR' ? '€' : (currency || '₺');
    return `${sym}${price.toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const availabilityBadge = (av: string | null) => {
    if (!av) return null;
    const inStock = av.toLowerCase().includes('instock') || av.toLowerCase().includes('in_stock');
    return (
      <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${inStock ? 'bg-emerald-500/20 text-emerald-600 dark:text-emerald-400' : 'bg-red-500/20 text-red-600 dark:text-red-400'}`}>
        {inStock ? 'In Stock' : 'Out of Stock'}
      </span>
    );
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-xl flex items-center justify-center`} style={{ background: `linear-gradient(135deg, ${platformColor}22, ${platformColor}44)` }}>
            {platformIcon}
          </div>
          <div>
            <h1 className="text-xl font-bold text-text-primary">{platformLabel} Products</h1>
            <p className="text-xs text-text-muted">
              {data ? `${data.total} products found` : 'Loading...'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="px-3 py-2 text-sm rounded-lg border border-border-default text-text-body hover:bg-accent-primary/5 transition-colors flex items-center gap-1.5"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
            </svg>
            Filters
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".xlsx,.xls"
            onChange={handleExcelImport}
            className="hidden"
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={importing}
            className="px-3 py-2 text-sm rounded-lg border border-border-default text-text-body hover:bg-accent-primary/5 transition-colors flex items-center gap-1.5 disabled:opacity-50"
          >
            {importing ? (
              <div className="w-4 h-4 border-2 border-neutral-400/30 border-t-neutral-400 rounded-full animate-spin" />
            ) : (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
            )}
            Import Excel
          </button>
          <button
            onClick={() => setShowUrlDialog(true)}
            disabled={scraping}
            className="px-3 py-2 text-sm rounded-lg border border-border-default text-text-body hover:bg-accent-primary/5 transition-colors flex items-center gap-1.5 disabled:opacity-50"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
            </svg>
            Scrape URLs
          </button>
          {platform !== 'web' && (
            <>
              <button
                onClick={handleBackfillPrices}
                className="px-3 py-2 text-sm rounded-lg border border-border-default text-text-body hover:bg-accent-primary/5 transition-colors flex items-center gap-1.5"
                title="Fill missing prices from Price Monitor data"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Backfill Prices
              </button>
              <button
                onClick={handleScrape}
                disabled={scraping}
                className="px-3 py-2 text-sm rounded-lg text-text-primary font-medium transition-all flex items-center gap-1.5 disabled:opacity-50"
                style={{ background: `linear-gradient(135deg, ${platformColor}, ${platformColor}cc)` }}
              >
                {scraping ? (
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                )}
                Scrape Products
              </button>
            </>
          )}
        </div>
      </div>

      {importMessage && (
        <div className="px-4 py-2.5 rounded-lg bg-accent-primary/5 border border-border-default text-sm text-text-body flex items-center justify-between">
          <span>{importMessage}</span>
          <button onClick={() => setImportMessage('')} className="text-neutral-500 dark:text-text-muted hover:text-text-primary ml-2">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
        </div>
      )}

      {(scrapeMessage || scrapeProgress) && (
        <div className="rounded-lg bg-accent-primary/5 border border-border-default overflow-hidden">
          <div className="px-4 py-2.5 flex items-center justify-between">
            <span className="text-sm text-text-body">{scrapeMessage}</span>
            {scrapeProgress && scrapeProgress.status !== 'completed' && scrapeProgress.status !== 'failed' && scrapeProgress.status !== 'stopped' && (
              <span className="text-xs text-neutral-500 dark:text-text-muted">
                {scrapeProgress.completed + scrapeProgress.failed} / {scrapeProgress.total}
              </span>
            )}
          </div>
          {scrapeProgress && scrapeProgress.total > 0 && (
            <div className="px-4 pb-3">
              <div className="w-full h-2 bg-accent-primary/5 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{
                    width: `${Math.round(((scrapeProgress.completed + scrapeProgress.failed) / scrapeProgress.total) * 100)}%`,
                    background: `linear-gradient(90deg, ${platformColor}, ${platformColor}99)`,
                  }}
                />
              </div>
              <div className="flex gap-4 mt-1.5 text-xs">
                <span className="text-green-600 dark:text-green-400">{scrapeProgress.completed} OK</span>
                {scrapeProgress.failed > 0 && <span className="text-red-600 dark:text-red-400">{scrapeProgress.failed} failed</span>}
                {scrapeProgress.pending > 0 && <span className="text-neutral-500 dark:text-text-muted">{scrapeProgress.pending} pending</span>}
                {scrapeProgress.skipped > 0 && <span className="text-yellow-600 dark:text-yellow-400">{scrapeProgress.skipped} skipped</span>}
              </div>
            </div>
          )}
        </div>
      )}

      <form onSubmit={handleSearch} className="flex gap-2">
        <div className="flex-1 relative">
          <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-500 dark:text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by name, brand, or SKU..."
            className="w-full pl-10 pr-4 py-2.5 rounded-lg bg-accent-primary/5 border border-border-default text-text-primary placeholder-neutral-500 text-sm focus:outline-none focus:border-accent-primary/50"
          />
        </div>
        <button type="submit" className="px-4 py-2.5 rounded-lg bg-accent-primary/5 border border-border-default text-text-primary text-sm hover:bg-accent-primary/[0.08] transition-colors">
          Search
        </button>
      </form>

      {showFilters && (
        <div className="rounded-xl border border-border-default p-4 space-y-3 bg-gradient-to-br from-white/[0.03] to-white/[0.01] dark:from-dark-800/50 dark:to-dark-900/50">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div>
              <label className="text-xs text-text-muted mb-1 block">Brand</label>
              <select
                value={selectedBrand}
                onChange={(e) => { setSelectedBrand(e.target.value); setPage(1); }}
                className="w-full px-3 py-2 rounded-lg bg-accent-primary/5 border border-border-default text-text-primary text-sm focus:outline-none focus:border-accent-primary/50"
              >
                <option value="">All Brands</option>
                {filters?.brands.map((b) => (
                  <option key={b.name} value={b.name}>{b.name} ({b.count})</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-text-muted mb-1 block">Category</label>
              <select
                value={selectedCategory}
                onChange={(e) => { setSelectedCategory(e.target.value); setPage(1); }}
                className="w-full px-3 py-2 rounded-lg bg-accent-primary/5 border border-border-default text-text-primary text-sm focus:outline-none focus:border-accent-primary/50"
              >
                <option value="">All Categories</option>
                {filters?.categories.map((c) => (
                  <option key={c.name} value={c.name}>{c.name} ({c.count})</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-text-muted mb-1 block">Min Price</label>
              <input
                type="number"
                value={minPrice}
                onChange={(e) => { setMinPrice(e.target.value); setPage(1); }}
                placeholder={filters?.price_range ? `Min: ${Math.floor(filters.price_range.min)}` : 'Min'}
                className="w-full px-3 py-2 rounded-lg bg-accent-primary/5 border border-border-default text-text-primary text-sm focus:outline-none focus:border-accent-primary/50"
              />
            </div>
            <div>
              <label className="text-xs text-text-muted mb-1 block">Max Price</label>
              <input
                type="number"
                value={maxPrice}
                onChange={(e) => { setMaxPrice(e.target.value); setPage(1); }}
                placeholder={filters?.price_range ? `Max: ${Math.ceil(filters.price_range.max)}` : 'Max'}
                className="w-full px-3 py-2 rounded-lg bg-accent-primary/5 border border-border-default text-text-primary text-sm focus:outline-none focus:border-accent-primary/50"
              />
            </div>
            <div>
              <label className="text-xs text-text-muted mb-1 block">Min Rating</label>
              <select
                value={minRating}
                onChange={(e) => { setMinRating(e.target.value); setPage(1); }}
                className="w-full px-3 py-2 rounded-lg bg-accent-primary/5 border border-border-default text-text-primary text-sm focus:outline-none focus:border-accent-primary/50"
              >
                <option value="">All Ratings</option>
                <option value="4">4+ Stars</option>
                <option value="3">3+ Stars</option>
                <option value="2">2+ Stars</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-text-muted mb-1 block">SKU</label>
              <input
                type="text"
                value={skuFilter}
                onChange={(e) => { setSkuFilter(e.target.value); setPage(1); }}
                placeholder="Exact SKU"
                className="w-full px-3 py-2 rounded-lg bg-accent-primary/5 border border-border-default text-text-primary text-sm focus:outline-none focus:border-accent-primary/50"
              />
            </div>
            <div>
              <label className="text-xs text-text-muted mb-1 block">Barcode</label>
              <input
                type="text"
                value={barcodeFilter}
                onChange={(e) => { setBarcodeFilter(e.target.value); setPage(1); }}
                placeholder="Exact Barcode"
                className="w-full px-3 py-2 rounded-lg bg-accent-primary/5 border border-border-default text-text-primary text-sm focus:outline-none focus:border-accent-primary/50"
              />
            </div>
            <div>
              <label className="text-xs text-text-muted mb-1 block">Sort By</label>
              <select
                value={`${sortBy}:${sortDir}`}
                onChange={(e) => {
                  const [sb, sd] = e.target.value.split(':');
                  setSortBy(sb);
                  setSortDir(sd);
                  setPage(1);
                }}
                className="w-full px-3 py-2 rounded-lg bg-accent-primary/5 border border-border-default text-text-primary text-sm focus:outline-none focus:border-accent-primary/50"
              >
                <option value="created_at:desc">Newest First</option>
                <option value="created_at:asc">Oldest First</option>
                <option value="price:asc">Price: Low to High</option>
                <option value="price:desc">Price: High to Low</option>
                <option value="rating:desc">Highest Rating</option>
                <option value="product_name:asc">Name A-Z</option>
                <option value="brand:asc">Brand A-Z</option>
              </select>
            </div>
          </div>
          <div className="flex justify-end">
            <button onClick={clearFilters} className="px-3 py-1.5 text-xs rounded-lg text-text-muted hover:text-text-primary hover:bg-accent-primary/5 transition-colors">
              Clear All Filters
            </button>
          </div>
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="w-8 h-8 border-2 border-t-transparent rounded-full animate-spin" style={{ borderColor: `${platformColor}44`, borderTopColor: platformColor }} />
        </div>
      ) : data && data.products.length > 0 ? (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-3">
            {data.products.map((product) => (
              <div
                key={product.id}
                onClick={() => setSelectedProduct(product)}
                className={`group rounded-xl border overflow-hidden cursor-pointer transition-all duration-200 bg-gradient-to-b from-white/[0.04] to-white/[0.01] dark:from-dark-800 dark:to-dark-900 ${
                  selectedProduct?.id === product.id
                    ? 'border-white/30 ring-1'
                    : 'border-border-default hover:border-white/20'
                }`}
                style={{
                  ...(selectedProduct?.id === product.id ? { ringColor: platformColor, borderColor: `${platformColor}66` } : {})
                }}
              >
                <div className="aspect-square relative overflow-hidden bg-surface-subtle">
                  {product.image_url ? (
                    <img
                      src={product.image_url}
                      alt={product.product_name || ''}
                      className="w-full h-full object-contain p-2 group-hover:scale-105 transition-transform duration-300"
                      loading="lazy"
                      onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-neutral-600">
                      <svg className="w-12 h-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                      </svg>
                    </div>
                  )}
                  {product.availability && availabilityBadge(product.availability) && (
                    <div className="absolute top-2 left-2">
                      {availabilityBadge(product.availability)}
                    </div>
                  )}
                  {product.platform && (
                    <div className="absolute top-2 right-2">
                      <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-black/50 text-text-body uppercase tracking-wider">
                        {product.platform}
                      </span>
                    </div>
                  )}
                </div>
                <div className="p-3 space-y-1.5">
                  {product.brand && (
                    <p className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: platformColor }}>
                      {product.brand}
                    </p>
                  )}
                  <h3 className="text-sm text-text-secondary font-medium line-clamp-2 leading-snug">
                    {product.product_name || 'Untitled'}
                  </h3>
                  {product.category && (
                    <p className="text-[10px] text-neutral-500 dark:text-text-muted truncate">{product.category}</p>
                  )}
                  <div className="flex items-center justify-between pt-1">
                    <span className="text-base font-bold text-text-primary">
                      {formatPrice(product.price, product.currency)}
                    </span>
                    {product.rating && renderStars(product.rating)}
                  </div>
                  <div className="flex items-center gap-2 text-[10px] text-neutral-500 dark:text-text-muted">
                    {product.sku && <span>SKU: {product.sku}</span>}
                    {product.review_count !== null && product.review_count !== undefined && (
                      <span>{product.review_count} reviews</span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {data.total_pages > 1 && (
            <div className="flex items-center justify-between pt-4">
              <p className="text-xs text-neutral-500 dark:text-text-muted">
                Page {data.page} of {data.total_pages} ({data.total} total)
              </p>
              <div className="flex gap-1">
                <button
                  onClick={() => setPage(Math.max(1, page - 1))}
                  disabled={page <= 1}
                  className="px-3 py-1.5 rounded-lg text-sm border border-border-default text-text-muted hover:bg-accent-primary/5 disabled:opacity-30 transition-colors"
                >
                  Prev
                </button>
                {Array.from({ length: Math.min(5, data.total_pages) }, (_, i) => {
                  const startPage = Math.max(1, Math.min(page - 2, data.total_pages - 4));
                  const p = startPage + i;
                  if (p > data.total_pages) return null;
                  return (
                    <button
                      key={p}
                      onClick={() => setPage(p)}
                      className={`px-3 py-1.5 rounded-lg text-sm border transition-colors ${
                        p === page
                          ? 'border-accent-primary/50 text-text-primary bg-accent-primary/10'
                          : 'border-border-default text-text-muted hover:bg-accent-primary/5'
                      }`}
                    >
                      {p}
                    </button>
                  );
                })}
                <button
                  onClick={() => setPage(Math.min(data.total_pages, page + 1))}
                  disabled={page >= data.total_pages}
                  className="px-3 py-1.5 rounded-lg text-sm border border-border-default text-text-muted hover:bg-accent-primary/5 disabled:opacity-30 transition-colors"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </>
      ) : (
        <div className="text-center py-20 space-y-3">
          <div className="w-16 h-16 mx-auto rounded-2xl flex items-center justify-center" style={{ background: `${platformColor}11` }}>
            <svg className="w-8 h-8" style={{ color: `${platformColor}44` }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
            </svg>
          </div>
          <p className="text-text-muted text-sm">No products found</p>
          <p className="text-neutral-500 dark:text-text-muted text-xs">
            {platform === 'web'
              ? 'Click "Import Excel" to upload product data, or "Scrape URLs" to fetch from a list of URLs.'
              : 'Click "Scrape Products" to fetch products from Price Monitor, "Import Excel", or "Scrape URLs".'}
          </p>
        </div>
      )}

      {showUrlDialog && createPortal(
        <>
          <div className="fixed inset-0 bg-black/60 z-[9998]" onClick={() => setShowUrlDialog(false)} />
          <div
            className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-xl z-[9999] rounded-xl border border-border-default shadow-2xl p-6 bg-gradient-to-b from-surface-card to-surface-input dark:from-dark-800 dark:to-dark-900"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-text-primary">Scrape URLs</h3>
              <button onClick={() => setShowUrlDialog(false)} className="p-1.5 hover:bg-accent-primary/[0.08] rounded-lg text-text-muted">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <p className="text-sm text-text-muted mb-3">Paste URLs below (one per line). Each URL will be scraped and saved as a product.</p>
            <textarea
              value={urlText}
              onChange={(e) => setUrlText(e.target.value)}
              placeholder={"https://www.hepsiburada.com/...\nhttps://www.trendyol.com/...\nhttps://example.com/product/..."}
              className="w-full h-48 bg-surface-subtle border border-border-default rounded-lg p-3 text-sm text-text-secondary placeholder:text-neutral-600 focus:outline-none focus:border-accent-primary/50 resize-none font-mono"
            />
            <div className="flex items-center justify-between mt-4">
              <span className="text-xs text-neutral-500 dark:text-text-muted">
                {urlText.split('\n').filter(u => u.trim() && (u.trim().startsWith('http://') || u.trim().startsWith('https://'))).length} valid URLs
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => setShowUrlDialog(false)}
                  className="px-4 py-2 text-sm rounded-lg border border-border-default text-text-body hover:bg-accent-primary/5"
                >
                  Cancel
                </button>
                <button
                  onClick={handleUrlScrape}
                  disabled={!urlText.trim()}
                  className="px-4 py-2 text-sm rounded-lg text-text-primary font-medium disabled:opacity-50"
                  style={{ background: 'linear-gradient(135deg, #00d4ff, #00d4ffcc)' }}
                >
                  Start Scraping
                </button>
              </div>
            </div>
          </div>
        </>,
        document.body
      )}

      {selectedProduct && createPortal(
        <>
          <div className="fixed inset-0 bg-black/50 z-[9998]" onClick={() => setSelectedProduct(null)} />
          <div
            className="fixed top-0 right-0 h-full w-full max-w-lg z-[9999] overflow-y-auto border-l border-border-default shadow-2xl bg-gradient-to-b from-surface-card to-surface-input dark:from-dark-800 dark:to-dark-900"
            onClick={(e) => e.stopPropagation()}
            onKeyDown={(e) => { if (e.key === 'Escape') setSelectedProduct(null); }}
            tabIndex={-1}
            ref={(el) => el?.focus()}
          >
            <div className="sticky top-0 z-10 flex items-center justify-between px-5 py-3 border-b border-border-default bg-surface-card/95 dark:bg-dark-800/95 backdrop-blur-xl">
              <div className="flex items-center gap-2 min-w-0">
                {selectedProduct.platform && (
                  <span className="text-[9px] font-bold px-1.5 py-0.5 rounded uppercase tracking-wider flex-shrink-0" style={{ background: `${platformColor}22`, color: platformColor }}>
                    {selectedProduct.platform}
                  </span>
                )}
                <h2 className="text-sm font-semibold text-text-primary truncate">{selectedProduct.product_name || 'Product Details'}</h2>
              </div>
              <button onClick={() => setSelectedProduct(null)} className="p-1.5 hover:bg-accent-primary/[0.08] rounded-lg transition-colors text-text-muted flex-shrink-0 ml-2">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="p-5 space-y-5">
              {selectedProduct.image_url && (
                <div className="rounded-xl overflow-hidden bg-surface-subtle border border-border-default">
                  <img src={selectedProduct.image_url} alt="" className="w-full object-contain max-h-64" />
                </div>
              )}
              {selectedProduct.images && selectedProduct.images.length > 1 && (
                <div className="flex gap-2 overflow-x-auto pb-1">
                  {selectedProduct.images.slice(0, 6).map((img, i) => (
                    <img key={i} src={img} alt="" className="w-14 h-14 object-contain rounded-lg border border-border-default bg-surface-subtle flex-shrink-0" />
                  ))}
                </div>
              )}

              <div>
                {selectedProduct.brand && (
                  <p className="text-xs font-semibold uppercase tracking-wider mb-1" style={{ color: platformColor }}>
                    {selectedProduct.brand}
                  </p>
                )}
                <h3 className="text-base font-bold text-text-primary leading-snug">{selectedProduct.product_name}</h3>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div className="rounded-lg p-3 bg-surface-subtle border border-border-default">
                  <p className="text-[10px] text-neutral-500 dark:text-text-muted uppercase tracking-wider">Price</p>
                  <p className={`text-xl font-bold mt-0.5 ${selectedProduct.price ? 'text-accent-primary' : 'text-text-muted'}`}>
                    {formatPrice(selectedProduct.price, selectedProduct.currency)}
                  </p>
                </div>
                <div className="rounded-lg p-3 bg-surface-subtle border border-border-default">
                  <p className="text-[10px] text-neutral-500 dark:text-text-muted uppercase tracking-wider">Rating</p>
                  <div className="mt-1">
                    {selectedProduct.rating ? renderStars(selectedProduct.rating) : <span className="text-neutral-500 dark:text-text-muted text-sm">N/A</span>}
                  </div>
                  {selectedProduct.review_count !== null && (
                    <p className="text-[10px] text-neutral-500 dark:text-text-muted mt-0.5">{selectedProduct.review_count} reviews</p>
                  )}
                </div>
              </div>

              <div className="space-y-1.5">
                {selectedProduct.sku && (
                  <div className="flex justify-between items-center py-1.5 border-b border-border-default">
                    <span className="text-xs text-neutral-500 dark:text-text-muted">SKU</span>
                    <span className="text-xs text-text-secondary font-mono">{selectedProduct.sku}</span>
                  </div>
                )}
                {selectedProduct.barcode && (
                  <div className="flex justify-between items-center py-1.5 border-b border-border-default">
                    <span className="text-xs text-neutral-500 dark:text-text-muted">Barcode</span>
                    <span className="text-xs text-text-secondary font-mono">{selectedProduct.barcode}</span>
                  </div>
                )}
                {selectedProduct.seller_name && (
                  <div className="flex justify-between items-center py-1.5 border-b border-border-default">
                    <span className="text-xs text-neutral-500 dark:text-text-muted">Seller</span>
                    <span className="text-xs text-text-secondary">{selectedProduct.seller_name}</span>
                  </div>
                )}
                {selectedProduct.availability && (
                  <div className="flex justify-between items-center py-1.5 border-b border-border-default">
                    <span className="text-xs text-neutral-500 dark:text-text-muted">Status</span>
                    {availabilityBadge(selectedProduct.availability)}
                  </div>
                )}
              </div>

              {selectedProduct.category_breadcrumbs && (
                <div>
                  <p className="text-[10px] text-neutral-500 dark:text-text-muted uppercase tracking-wider mb-1.5">Category</p>
                  <div className="flex flex-wrap items-center gap-1 text-xs">
                    {selectedProduct.category_breadcrumbs.map((bc, i) => (
                      <span key={i} className="flex items-center gap-1">
                        {i > 0 && <span className="text-neutral-600">&rsaquo;</span>}
                        {bc.url ? (
                          <a href={bc.url} target="_blank" rel="noopener noreferrer" className="text-accent-primary hover:text-text-primary transition-colors">
                            {bc.name}
                          </a>
                        ) : (
                          <span className="text-text-body">{bc.name}</span>
                        )}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {selectedProduct.shipping_info && (
                <div className="text-xs text-text-muted flex items-center gap-1.5">
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 17h1m7 0h1M3 9h18M3 9l2.5-4h13L21 9M3 9v8a1 1 0 001 1h16a1 1 0 001-1V9" /></svg>
                  Shipping: {selectedProduct.shipping_info.cost} {selectedProduct.shipping_info.currency}
                </div>
              )}

              {selectedProduct.return_policy && (
                <div className="text-xs text-text-muted flex items-center gap-1.5">
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6" /></svg>
                  Return: {selectedProduct.return_policy.days} days{selectedProduct.return_policy.free_return ? ' (Free)' : ''}
                </div>
              )}

              <a
                href={selectedProduct.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center justify-center gap-1.5 w-full px-4 py-2.5 rounded-lg text-sm font-medium text-text-primary transition-all hover:brightness-110"
                style={{ background: `linear-gradient(135deg, ${platformColor}, ${platformColor}cc)` }}
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
                View on {selectedProduct.platform}
              </a>

              {selectedProduct.product_specs && Object.keys(selectedProduct.product_specs).length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-text-body uppercase tracking-wider mb-2">Specifications</p>
                  <div className="space-y-1">
                    {Object.entries(selectedProduct.product_specs).map(([key, val]) => (
                      <div key={key} className="flex gap-2 text-xs py-1.5 px-2.5 rounded bg-white/[0.02]">
                        <span className="text-neutral-500 dark:text-text-muted min-w-[100px] flex-shrink-0">{key}</span>
                        <span className="text-text-body">{val}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {selectedProduct.reviews && selectedProduct.reviews.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-text-body uppercase tracking-wider mb-2">Reviews ({selectedProduct.reviews.length})</p>
                  <div className="space-y-2 max-h-60 overflow-y-auto">
                    {selectedProduct.reviews.map((rev, i) => (
                      <div key={i} className="p-3 rounded-lg bg-white/[0.02] dark:bg-dark-800/50 border border-border-default">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-xs text-text-muted">{rev.author || 'Anonymous'}</span>
                          <div className="flex items-center gap-2">
                            {rev.rating && renderStars(rev.rating)}
                            {rev.date && <span className="text-[10px] text-neutral-500 dark:text-text-muted">{rev.date}</span>}
                          </div>
                        </div>
                        <p className="text-xs text-text-body leading-relaxed">{rev.text}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {selectedProduct.description && (
                <div>
                  <p className="text-xs font-semibold text-text-body uppercase tracking-wider mb-2">Description</p>
                  <p className="text-xs text-text-muted leading-relaxed line-clamp-6">{selectedProduct.description}</p>
                </div>
              )}

              <div className="h-6" />
            </div>
          </div>
        </>,
        document.body
      )}
    </div>
  );
}
