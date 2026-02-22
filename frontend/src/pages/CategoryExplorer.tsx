import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { createPortal } from 'react-dom';
import {
  getStoreProducts,
  getStoreProductFilters,
  getStoreCategoryTree,
  getCategoryProductsByCategory,
  getCategoryPageFilters,
  scrapeCategoryPage,
  fetchCategoryProductDetail,
  getCategoryFetchStatus,
  type StoreProduct,
  type StoreProductFilters,
  type StoreProductListResponse,
  type CategoryTreeNode,
  type CategoryProductItem,
  type CategoryProductListResponse,
  type CategoryFilterData,
} from '../services/api';

type Platform = '' | 'hepsiburada' | 'trendyol' | 'web';
type ViewMode = 'my_products' | 'category_page';

export default function CategoryExplorer() {
  const [platform, setPlatform] = useState<Platform>('');
  const [viewMode, setViewMode] = useState<ViewMode>('my_products');
  const [data, setData] = useState<StoreProductListResponse | null>(null);
  const [catData, setCatData] = useState<CategoryProductListResponse | null>(null);
  const [filters, setFilters] = useState<StoreProductFilters | null>(null);
  const [categoryTree, setCategoryTree] = useState<CategoryTreeNode[]>([]);
  const [loading, setLoading] = useState(true);

  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [selectedBrand, setSelectedBrand] = useState('');
  const [minPrice, setMinPrice] = useState('');
  const [maxPrice, setMaxPrice] = useState('');
  const [minRating, setMinRating] = useState('');
  const [sortBy, setSortBy] = useState('created_at');
  const [sortDir, setSortDir] = useState('desc');
  const [page, setPage] = useState(1);
  const [pageSize] = useState(50);

  const [selectedProduct, setSelectedProduct] = useState<StoreProduct | null>(null);
  const [selectedCatProduct, setSelectedCatProduct] = useState<CategoryProductItem | null>(null);
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set());
  const [showScraper, setShowScraper] = useState(false);
  const [scrapeUrl, setScrapeUrl] = useState('');
  const [scrapePageCount, setScrapePageCount] = useState(1);
  const [scraping, setScraping] = useState(false);
  const [scrapeMsg, setScrapeMsg] = useState('');
  const [scrapeProgress, setScrapeProgress] = useState('');
  const [scrapeSessionId, setScrapeSessionId] = useState<string | null>(null);
  const [showMobileFilters, setShowMobileFilters] = useState(false);

  const [catFilterData, setCatFilterData] = useState<CategoryFilterData | null>(null);
  const [catBrand, setCatBrand] = useState('');
  const [catSeller, setCatSeller] = useState('');
  const [catMinPrice, setCatMinPrice] = useState('');
  const [catMaxPrice, setCatMaxPrice] = useState('');
  const [catMinRating, setCatMinRating] = useState('');
  const [catSponsored, setCatSponsored] = useState<'' | 'true' | 'false'>('');
  const [catSortBy, setCatSortBy] = useState('position');
  const [catSortDir, setCatSortDir] = useState('asc');

  const [showDetailPanel, setShowDetailPanel] = useState(false);
  const [selectedForDetail, setSelectedForDetail] = useState<Set<number>>(new Set());
  const [detailFetching, setDetailFetching] = useState(false);
  const [detailProgress, setDetailProgress] = useState('');
  const detailPollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchMyProducts = useCallback(async () => {
    setLoading(true);
    try {
      const params: any = {
        platform: platform || undefined,
        page,
        page_size: pageSize,
        sort_by: sortBy,
        sort_dir: sortDir,
      };
      if (search) params.search = search;
      if (selectedCategory) params.category = selectedCategory;
      if (selectedBrand) params.brand = selectedBrand;
      if (minPrice) params.min_price = parseFloat(minPrice);
      if (maxPrice) params.max_price = parseFloat(maxPrice);
      if (minRating) params.min_rating = parseFloat(minRating);
      const result = await getStoreProducts(params);
      setData(result);
    } catch (err) {
      console.error('Failed to load products:', err);
    } finally {
      setLoading(false);
    }
  }, [platform, page, pageSize, sortBy, sortDir, search, selectedCategory, selectedBrand, minPrice, maxPrice, minRating]);

  const fetchCatProducts = useCallback(async () => {
    setLoading(true);
    try {
      const params: any = {
        page,
        page_size: pageSize,
        sort_by: catSortBy,
        sort_dir: catSortDir,
      };
      if (platform) params.platform = platform;
      if (scrapeSessionId) params.session_id = scrapeSessionId;
      else if (selectedCategory) params.category = selectedCategory;
      if (search) params.search = search;
      if (catBrand) params.brand = catBrand;
      if (catSeller) params.seller = catSeller;
      if (catMinPrice) params.min_price = parseFloat(catMinPrice);
      if (catMaxPrice) params.max_price = parseFloat(catMaxPrice);
      if (catMinRating) params.min_rating = parseFloat(catMinRating);
      if (catSponsored === 'true') params.is_sponsored = true;
      else if (catSponsored === 'false') params.is_sponsored = false;
      const result = await getCategoryProductsByCategory(params);
      setCatData(result);
    } catch (err) {
      console.error('Failed to load category products:', err);
    } finally {
      setLoading(false);
    }
  }, [platform, page, pageSize, selectedCategory, search, scrapeSessionId, catBrand, catSeller, catMinPrice, catMaxPrice, catMinRating, catSponsored, catSortBy, catSortDir]);

  const fetchFilters = useCallback(async () => {
    try {
      const [f, tree] = await Promise.all([
        getStoreProductFilters(platform || undefined),
        getStoreCategoryTree(platform || undefined),
      ]);
      setFilters(f);
      setCategoryTree(tree.tree);
    } catch {}
  }, [platform]);

  const fetchCatFilterData = useCallback(async () => {
    try {
      const params: any = {};
      if (platform) params.platform = platform;
      if (scrapeSessionId) params.session_id = scrapeSessionId;
      else if (selectedCategory) params.category = selectedCategory;
      const result = await getCategoryPageFilters(params);
      setCatFilterData(result);
    } catch {}
  }, [platform, scrapeSessionId, selectedCategory]);

  useEffect(() => {
    if (viewMode === 'my_products') fetchMyProducts();
    else fetchCatProducts();
  }, [viewMode, fetchMyProducts, fetchCatProducts]);

  useEffect(() => { fetchFilters(); }, [fetchFilters]);

  useEffect(() => {
    if (viewMode === 'category_page') fetchCatFilterData();
  }, [viewMode, fetchCatFilterData]);

  useEffect(() => {
    setPage(1);
  }, [platform, search, selectedCategory, selectedBrand, minPrice, maxPrice, minRating, sortBy, sortDir, viewMode, catBrand, catSeller, catMinPrice, catMaxPrice, catMinRating, catSponsored, catSortBy, catSortDir]);

  const categoryUrlMap = useMemo(() => {
    const map: Record<string, string> = {};
    const walk = (nodes: CategoryTreeNode[]) => {
      for (const node of nodes) {
        if (node.category_url) {
          map[node.full_path] = node.category_url;
        }
        if (node.children?.length) walk(node.children);
      }
    };
    walk(categoryTree);
    return map;
  }, [categoryTree]);

  useEffect(() => {
    if (!selectedCategory) {
      setScrapeUrl('');
      return;
    }

    if (categoryUrlMap[selectedCategory]) {
      setScrapeUrl(categoryUrlMap[selectedCategory]);
      setScrapeSessionId('');
      setShowScraper(true);
      return;
    }

    const parts = selectedCategory.split(' > ');
    for (let i = parts.length - 1; i >= 0; i--) {
      const partial = parts.slice(0, i + 1).join(' > ');
      if (categoryUrlMap[partial]) {
        setScrapeUrl(categoryUrlMap[partial]);
        setScrapeSessionId('');
        setShowScraper(true);
        return;
      }
    }

    setScrapeUrl('');
  }, [selectedCategory, categoryUrlMap]);

  useEffect(() => {
    return () => {
      if (detailPollRef.current) clearInterval(detailPollRef.current);
    };
  }, []);

  const handlePlatformChange = (p: Platform) => {
    setPlatform(p);
    setSelectedCategory('');
    setSelectedBrand('');
    setExpandedCategories(new Set());
  };

  const toggleCategory = (fullPath: string) => {
    setExpandedCategories(prev => {
      const next = new Set(prev);
      if (next.has(fullPath)) next.delete(fullPath);
      else next.add(fullPath);
      return next;
    });
  };

  const selectCategory = (fullPath: string) => {
    setSelectedCategory(prev => prev === fullPath ? '' : fullPath);
    setPage(1);
  };

  const handleScrape = async () => {
    if (!scrapeUrl) return;
    setScraping(true);
    setScrapeMsg('');
    setScrapeProgress('');
    try {
      setScrapeProgress(`Scraping ${scrapePageCount} page${scrapePageCount > 1 ? 's' : ''}...`);
      const result = await scrapeCategoryPage(scrapeUrl, 1, scrapeSessionId || undefined, scrapePageCount);
      const pagesScraped = result.pages_scraped_list?.length || 1;
      setScrapeMsg(`Done: ${result.products_added} new products from ${pagesScraped} page${pagesScraped > 1 ? 's' : ''} (${result.products_found} found, ${result.total_in_session} total)`);
      setScrapeProgress('');
      if (result.session?.id) setScrapeSessionId(result.session.id);
      if (result.session?.filter_data) {
        const fd = result.session.filter_data;
        setCatFilterData(prev => ({
          brands: fd.brands || prev?.brands || [],
          sellers: fd.sellers || prev?.sellers || [],
          price_range: prev?.price_range || { min: 0, max: 0 },
        }));
      }
      if (viewMode === 'category_page') {
        fetchCatProducts();
        fetchCatFilterData();
      }
    } catch (err: any) {
      setScrapeMsg(err?.response?.data?.detail || 'Scrape failed');
      setScrapeProgress('');
    } finally {
      setScraping(false);
    }
  };

  const toggleProductSelection = (id: number) => {
    setSelectedForDetail(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectAllForDetail = () => {
    const products = catData?.products || [];
    const unfetched = products.filter(p => !p.detail_fetched);
    if (selectedForDetail.size === unfetched.length && unfetched.length > 0) {
      setSelectedForDetail(new Set());
    } else {
      setSelectedForDetail(new Set(unfetched.map(p => p.id)));
    }
  };

  const handleFetchDetails = async () => {
    if (selectedForDetail.size === 0) return;
    setDetailFetching(true);
    setDetailProgress(`Starting detail fetch for ${selectedForDetail.size} products...`);
    try {
      const ids = Array.from(selectedForDetail);
      await fetchCategoryProductDetail(ids);
      setDetailProgress(`Fetching details for ${ids.length} products in background...`);

      const sessionId = scrapeSessionId || catData?.sessions?.[0]?.id;
      if (sessionId) {
        detailPollRef.current = setInterval(async () => {
          try {
            const status = await getCategoryFetchStatus(sessionId);
            setDetailProgress(`Details: ${status.detail_fetched}/${status.total_products} fetched (${status.pending} remaining)`);
            if (status.pending === 0) {
              if (detailPollRef.current) clearInterval(detailPollRef.current);
              setDetailFetching(false);
              setDetailProgress('All details fetched!');
              setSelectedForDetail(new Set());
              fetchCatProducts();
            }
          } catch {
            if (detailPollRef.current) clearInterval(detailPollRef.current);
            setDetailFetching(false);
          }
        }, 3000);
      } else {
        setTimeout(() => {
          setDetailFetching(false);
          setDetailProgress('Detail fetch started. Refresh to see results.');
          setSelectedForDetail(new Set());
        }, 2000);
      }
    } catch (err: any) {
      setDetailProgress(err?.response?.data?.detail || 'Detail fetch failed');
      setDetailFetching(false);
    }
  };

  const formatPrice = (price: number | null | undefined) => {
    if (!price) return '-';
    return new Intl.NumberFormat('tr-TR', { style: 'currency', currency: 'TRY', minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(price);
  };

  const breadcrumbParts = useMemo(() => {
    if (!selectedCategory) return [];
    return selectedCategory.split(' > ').map((part, i, arr) => ({
      name: part.trim(),
      path: arr.slice(0, i + 1).join(' > '),
    }));
  }, [selectedCategory]);

  const platformStats = useMemo(() => {
    if (!filters) return { total: 0, hb: 0, ty: 0, web: 0 };
    const pmap: Record<string, number> = {};
    filters.platforms.forEach(p => { pmap[p.name] = p.count; });
    return {
      total: Object.values(pmap).reduce((a, b) => a + b, 0),
      hb: pmap['hepsiburada'] || 0,
      ty: pmap['trendyol'] || 0,
      web: pmap['web'] || 0,
    };
  }, [filters]);

  const dynamicStats = useMemo(() => {
    if (viewMode === 'my_products' && data) {
      return {
        total: data.total,
        avgPrice: data.filtered_stats?.avg_price || 0,
        brandCount: data.filtered_stats?.brand_count || 0,
        categoryCount: data.filtered_stats?.category_count || 0,
        sellerCount: 0,
        lastScraped: null as string | null,
      };
    }
    if (viewMode === 'category_page' && catData) {
      return {
        total: catData.total,
        avgPrice: catData.filtered_stats?.avg_price || 0,
        brandCount: catData.filtered_stats?.brand_count || 0,
        categoryCount: 0,
        sellerCount: catData.filtered_stats?.seller_count || 0,
        lastScraped: catData.filtered_stats?.last_scraped || null,
      };
    }
    return { total: 0, avgPrice: 0, brandCount: 0, categoryCount: 0, sellerCount: 0, lastScraped: null as string | null };
  }, [viewMode, data, catData]);

  const detailStats = useMemo(() => {
    const products = catData?.products || [];
    const fetched = products.filter(p => p.detail_fetched).length;
    const unfetched = products.filter(p => !p.detail_fetched).length;
    return { total: products.length, fetched, unfetched };
  }, [catData]);

  const currentProducts = viewMode === 'my_products' ? data?.products || [] : [];
  const currentCatProducts = viewMode === 'category_page' ? catData?.products || [] : [];
  const currentTotal = viewMode === 'my_products' ? data?.total || 0 : catData?.total || 0;
  const currentTotalPages = viewMode === 'my_products' ? data?.total_pages || 0 : catData?.total_pages || 0;

  const renderCategoryNode = (node: CategoryTreeNode, depth: number = 0) => {
    const isSelected = selectedCategory === node.full_path;
    const isExpanded = expandedCategories.has(node.full_path);
    const hasChildren = node.children && node.children.length > 0;
    const isAncestor = selectedCategory.startsWith(node.full_path + ' > ');

    return (
      <div key={node.full_path}>
        <div
          className={`flex items-center gap-1 py-1.5 px-2 rounded-md cursor-pointer text-sm transition-colors group ${
            isSelected ? 'bg-cyan-500/15 text-cyan-300' : isAncestor ? 'text-cyan-400/70' : 'text-neutral-400 hover:text-neutral-200 hover:bg-white/5'
          }`}
          style={{ paddingLeft: `${depth * 14 + 8}px` }}
        >
          {hasChildren && (
            <button
              onClick={(e) => { e.stopPropagation(); toggleCategory(node.full_path); }}
              className="p-0.5 hover:bg-white/10 rounded flex-shrink-0"
            >
              <svg className={`w-3 h-3 transition-transform ${isExpanded ? 'rotate-90' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </button>
          )}
          {!hasChildren && <span className="w-4" />}
          <span className="flex-1 truncate" onClick={() => selectCategory(node.full_path)}>
            {node.name}
          </span>
          <span className="text-[10px] text-neutral-600 group-hover:text-neutral-500 flex-shrink-0">{node.count}</span>
        </div>
        {hasChildren && isExpanded && (
          <div>
            {node.children.map(child => renderCategoryNode(child, depth + 1))}
          </div>
        )}
      </div>
    );
  };

  const renderProductCard = (product: StoreProduct) => (
    <div
      key={product.id}
      className="rounded-xl border border-white/10 overflow-hidden hover:border-white/20 transition-all cursor-pointer group"
      style={{ background: 'linear-gradient(180deg, #141619 0%, #0e0f11 100%)' }}
      onClick={() => { setSelectedProduct(product); setSelectedCatProduct(null); }}
    >
      <div className="flex gap-3 p-3">
        <div className="w-20 h-20 rounded-lg bg-white/5 flex items-center justify-center flex-shrink-0 overflow-hidden">
          {product.image_url ? (
            <img src={product.image_url} alt="" className="max-h-full max-w-full object-contain" loading="lazy" />
          ) : (
            <svg className="w-8 h-8 text-neutral-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
          )}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 mb-1">
            <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${
              product.platform === 'hepsiburada' ? 'bg-orange-500/20 text-orange-400' :
              product.platform === 'trendyol' ? 'bg-purple-500/20 text-purple-400' :
              'bg-blue-500/20 text-blue-400'
            }`}>
              {product.platform === 'hepsiburada' ? 'HB' : product.platform === 'trendyol' ? 'TY' : 'WEB'}
            </span>
            {product.brand && <span className="text-[10px] text-cyan-400 font-medium uppercase truncate">{product.brand}</span>}
          </div>
          <h3 className="text-sm text-neutral-200 line-clamp-2 leading-snug mb-1.5">{product.product_name || 'Unnamed'}</h3>
          <div className="flex items-end justify-between">
            <span className="text-base font-bold text-white">{formatPrice(product.price)}</span>
            {product.rating && (
              <div className="flex items-center gap-0.5">
                <svg className="w-3 h-3 text-amber-400 fill-current" viewBox="0 0 20 20"><path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" /></svg>
                <span className="text-xs text-neutral-400">{product.rating}</span>
                {product.review_count != null && <span className="text-[10px] text-neutral-600">({product.review_count})</span>}
              </div>
            )}
          </div>
        </div>
      </div>
      {product.category && (
        <div className="px-3 pb-2.5">
          <p className="text-[10px] text-neutral-600 truncate">{product.category}</p>
        </div>
      )}
    </div>
  );

  const renderCatProductCard = (product: CategoryProductItem) => {
    const isSelected = selectedForDetail.has(product.id);
    return (
      <div
        key={product.id}
        className={`rounded-xl border overflow-hidden transition-all cursor-pointer group relative ${
          isSelected ? 'border-cyan-500/40 ring-1 ring-cyan-500/20' : 'border-white/10 hover:border-white/20'
        }`}
        style={{ background: 'linear-gradient(180deg, #141619 0%, #0e0f11 100%)' }}
      >
        <div className="absolute top-2 right-2 flex items-center gap-1 z-10">
          {showDetailPanel && !product.detail_fetched && (
            <button
              onClick={(e) => { e.stopPropagation(); toggleProductSelection(product.id); }}
              className={`w-5 h-5 rounded border flex items-center justify-center transition-colors ${
                isSelected ? 'bg-cyan-500 border-cyan-500 text-white' : 'border-white/20 hover:border-cyan-500/50'
              }`}
            >
              {isSelected && (
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" /></svg>
              )}
            </button>
          )}
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/10 text-neutral-400 font-mono">
            #{product.position}
          </span>
          {product.is_sponsored && (
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-400 font-medium">
              AD
            </span>
          )}
          {product.detail_fetched && (
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400 font-medium">
              Detailed
            </span>
          )}
        </div>
        <div
          className="flex gap-3 p-3"
          onClick={() => { setSelectedCatProduct(product); setSelectedProduct(null); }}
        >
          <div className="w-20 h-20 rounded-lg bg-white/5 flex items-center justify-center flex-shrink-0 overflow-hidden">
            {product.image_url ? (
              <img src={product.image_url} alt="" className="max-h-full max-w-full object-contain" loading="lazy" />
            ) : (
              <svg className="w-8 h-8 text-neutral-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
            )}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-1.5 mb-1">
              {product.brand && <span className="text-[10px] text-cyan-400 font-medium uppercase truncate">{product.brand}</span>}
            </div>
            <h3 className="text-sm text-neutral-200 line-clamp-2 leading-snug mb-1.5">{product.name || 'Unnamed'}</h3>
            <div className="flex items-end justify-between">
              <div className="flex items-center gap-2">
                <span className="text-base font-bold text-white">{formatPrice(product.price)}</span>
                {product.original_price && product.original_price > (product.price || 0) && (
                  <span className="text-xs text-neutral-500 line-through">{formatPrice(product.original_price)}</span>
                )}
              </div>
              {product.rating && (
                <div className="flex items-center gap-0.5">
                  <svg className="w-3 h-3 text-amber-400 fill-current" viewBox="0 0 20 20"><path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" /></svg>
                  <span className="text-xs text-neutral-400">{product.rating}</span>
                  {product.review_count != null && <span className="text-[10px] text-neutral-600">({product.review_count})</span>}
                </div>
              )}
            </div>
          </div>
        </div>
        <div className="px-3 pb-2.5 flex items-center justify-between">
          <div className="flex items-center gap-1.5 min-w-0">
            <span className="text-[10px] text-neutral-600">Page {product.page_number}</span>
            {product.seller_name && <span className="text-[10px] text-neutral-600 truncate">| {product.seller_name}</span>}
            {product.sku && <span className="text-[10px] text-neutral-600 font-mono truncate">SKU: {product.sku}</span>}
          </div>
          {product.campaign_text && (
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400 truncate max-w-[120px]">{product.campaign_text}</span>
          )}
        </div>
      </div>
    );
  };

  const FilterSidebar = () => (
    <div className="space-y-4">
      <div>
        <h3 className="text-xs font-medium text-neutral-500 uppercase tracking-wider mb-2 px-2">Platform</h3>
        <div className="space-y-0.5">
          {[
            { key: '' as Platform, label: 'All Platforms', count: platformStats.total, color: 'text-neutral-300' },
            { key: 'hepsiburada' as Platform, label: 'Hepsiburada', count: platformStats.hb, color: 'text-orange-400' },
            { key: 'trendyol' as Platform, label: 'Trendyol', count: platformStats.ty, color: 'text-purple-400' },
            { key: 'web' as Platform, label: 'Web', count: platformStats.web, color: 'text-blue-400' },
          ].map(p => (
            <button
              key={p.key}
              onClick={() => handlePlatformChange(p.key)}
              className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-colors ${
                platform === p.key ? 'bg-white/10 text-white' : 'text-neutral-400 hover:bg-white/5 hover:text-neutral-200'
              }`}
            >
              <span className={platform === p.key ? p.color : ''}>{p.label}</span>
              <span className="text-[10px] text-neutral-600">{p.count}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="border-t border-white/5 pt-3">
        <h3 className="text-xs font-medium text-neutral-500 uppercase tracking-wider mb-2 px-2">Categories</h3>
        <div className="max-h-[300px] overflow-y-auto custom-scrollbar">
          {categoryTree.length > 0 ? (
            categoryTree.map(node => renderCategoryNode(node))
          ) : (
            <p className="text-xs text-neutral-600 px-2">No categories</p>
          )}
        </div>
      </div>

      {viewMode === 'my_products' && (
        <>
          <div className="border-t border-white/5 pt-3">
            <h3 className="text-xs font-medium text-neutral-500 uppercase tracking-wider mb-2 px-2">Brand</h3>
            <select
              value={selectedBrand}
              onChange={(e) => { setSelectedBrand(e.target.value); setPage(1); }}
              className="w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-neutral-200 focus:outline-none focus:border-cyan-500/50"
            >
              <option value="">All Brands</option>
              {filters?.brands.map(b => (
                <option key={b.name} value={b.name}>{b.name} ({b.count})</option>
              ))}
            </select>
          </div>

          <div className="border-t border-white/5 pt-3">
            <h3 className="text-xs font-medium text-neutral-500 uppercase tracking-wider mb-2 px-2">Price Range</h3>
            <div className="flex gap-2 px-1">
              <input type="number" placeholder="Min" value={minPrice} onChange={(e) => setMinPrice(e.target.value)}
                className="w-1/2 bg-black/30 border border-white/10 rounded-lg px-2.5 py-1.5 text-sm text-neutral-200 focus:outline-none focus:border-cyan-500/50" />
              <input type="number" placeholder="Max" value={maxPrice} onChange={(e) => setMaxPrice(e.target.value)}
                className="w-1/2 bg-black/30 border border-white/10 rounded-lg px-2.5 py-1.5 text-sm text-neutral-200 focus:outline-none focus:border-cyan-500/50" />
            </div>
          </div>

          <div className="border-t border-white/5 pt-3">
            <h3 className="text-xs font-medium text-neutral-500 uppercase tracking-wider mb-2 px-2">Min Rating</h3>
            <select
              value={minRating}
              onChange={(e) => { setMinRating(e.target.value); setPage(1); }}
              className="w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-neutral-200 focus:outline-none focus:border-cyan-500/50"
            >
              <option value="">Any</option>
              <option value="4">4+ Stars</option>
              <option value="3">3+ Stars</option>
              <option value="2">2+ Stars</option>
              <option value="1">1+ Stars</option>
            </select>
          </div>
        </>
      )}

      {(selectedCategory || selectedBrand || minPrice || maxPrice || minRating) && (
        <div className="border-t border-white/5 pt-3">
          <button
            onClick={() => {
              setSelectedCategory('');
              setSelectedBrand('');
              setMinPrice('');
              setMaxPrice('');
              setMinRating('');
              setExpandedCategories(new Set());
            }}
            className="w-full px-3 py-2 text-sm rounded-lg border border-red-500/20 text-red-400 hover:bg-red-500/10 transition-colors"
          >
            Clear All Filters
          </button>
        </div>
      )}
    </div>
  );

  const Pagination = () => {
    if (currentTotalPages <= 1) return null;
    return (
      <div className="flex items-center justify-center gap-2 pt-4">
        <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page <= 1}
          className="px-3 py-2 text-sm rounded-lg border border-white/10 text-neutral-300 hover:bg-white/5 disabled:opacity-30">Previous</button>
        <div className="flex items-center gap-1">
          {Array.from({ length: Math.min(5, currentTotalPages) }, (_, i) => {
            let p: number;
            if (currentTotalPages <= 5) p = i + 1;
            else if (page <= 3) p = i + 1;
            else if (page >= currentTotalPages - 2) p = currentTotalPages - 4 + i;
            else p = page - 2 + i;
            return (
              <button key={p} onClick={() => setPage(p)}
                className={`w-9 h-9 text-sm rounded-lg ${p === page ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30' : 'text-neutral-400 hover:bg-white/5'}`}
              >{p}</button>
            );
          })}
        </div>
        <button onClick={() => setPage(p => Math.min(currentTotalPages, p + 1))} disabled={page >= currentTotalPages}
          className="px-3 py-2 text-sm rounded-lg border border-white/10 text-neutral-300 hover:bg-white/5 disabled:opacity-30">Next</button>
        <span className="text-xs text-neutral-600 ml-2">{currentTotal.toLocaleString()} products</span>
      </div>
    );
  };

  return (
    <div className="flex gap-6 pb-10 min-h-[calc(100vh-80px)]">
      <aside className="hidden lg:block w-64 flex-shrink-0">
        <div className="sticky top-4 rounded-xl border border-white/10 p-4 overflow-hidden" style={{ background: 'linear-gradient(180deg, #141619 0%, #0e0f11 100%)' }}>
          <FilterSidebar />
        </div>
      </aside>

      <main className="flex-1 min-w-0 space-y-5">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-xs text-neutral-500 uppercase tracking-wider mb-1">Competitive Analysis</div>
            <h1 className="text-2xl font-bold text-white">Category Explorer</h1>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={() => setShowMobileFilters(true)}
              className="lg:hidden px-3 py-2 text-sm rounded-lg border border-white/10 text-neutral-300 hover:bg-white/5">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" /></svg>
            </button>
            {viewMode === 'category_page' && (
              <button
                onClick={() => { setShowDetailPanel(!showDetailPanel); setSelectedForDetail(new Set()); }}
                className={`px-3 py-2 text-sm rounded-lg border transition-colors flex items-center gap-1.5 ${
                  showDetailPanel ? 'border-purple-500/30 bg-purple-500/10 text-purple-400' : 'border-white/10 text-neutral-300 hover:bg-white/5'
                }`}
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
                </svg>
                Get Details
              </button>
            )}
            <button
              onClick={() => setShowScraper(!showScraper)}
              className={`px-3 py-2 text-sm rounded-lg border transition-colors flex items-center gap-1.5 ${
                showScraper ? 'border-cyan-500/30 bg-cyan-500/10 text-cyan-400' : 'border-white/10 text-neutral-300 hover:bg-white/5'
              }`}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
              </svg>
              Scrape New
            </button>
          </div>
        </div>

        {showScraper && (
          <div className="rounded-xl border border-cyan-500/20 overflow-hidden" style={{ background: 'linear-gradient(135deg, rgba(0,212,255,0.05), rgba(0,212,255,0.02))' }}>
            <div className="p-4 space-y-3">
              <div className="flex items-center gap-2 mb-1">
                <svg className="w-4 h-4 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
                </svg>
                <span className="text-sm font-medium text-cyan-300">Scrape Category Page</span>
                <span className="text-[10px] text-neutral-500 ml-auto">Step 1: Collect product listings from marketplace</span>
              </div>

              <div className="flex flex-col sm:flex-row gap-3">
                <input
                  type="text"
                  value={scrapeUrl}
                  onChange={(e) => setScrapeUrl(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter' && !scraping) handleScrape(); }}
                  placeholder="Paste category URL — e.g. https://www.hepsiburada.com/hizli-cilalar-c-20035738"
                  className="flex-1 bg-black/30 border border-white/10 rounded-lg px-4 py-2.5 text-sm text-neutral-200 placeholder:text-neutral-600 focus:outline-none focus:border-cyan-500/50"
                />
              </div>

              <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
                <div className="flex items-center gap-2">
                  <label className="text-xs text-neutral-400 whitespace-nowrap">Pages to scrape:</label>
                  <div className="flex items-center gap-1">
                    {[1, 2, 3, 5, 10].map(n => (
                      <button
                        key={n}
                        onClick={() => setScrapePageCount(n)}
                        className={`px-2.5 py-1 text-xs rounded-md transition-colors ${
                          scrapePageCount === n
                            ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                            : 'bg-white/5 text-neutral-400 border border-white/10 hover:bg-white/10'
                        }`}
                      >
                        {n}
                      </button>
                    ))}
                    <input
                      type="number"
                      min={1}
                      max={20}
                      value={scrapePageCount}
                      onChange={(e) => setScrapePageCount(Math.max(1, Math.min(20, parseInt(e.target.value) || 1)))}
                      className="w-14 bg-black/30 border border-white/10 rounded-md px-2 py-1 text-xs text-neutral-200 text-center focus:outline-none focus:border-cyan-500/50"
                    />
                  </div>
                </div>

                <div className="flex items-center gap-2 sm:ml-auto">
                  {scrapeUrl && (
                    <span className="text-[10px] text-neutral-500">
                      {scrapeUrl.includes('hepsiburada') ? 'HB' : scrapeUrl.includes('trendyol') ? 'TY' : 'URL'}
                      {scrapePageCount > 1 && ` • ${scrapePageCount} pages: ${
                        scrapeUrl.includes('trendyol') ? '?pi=1...' + scrapePageCount : '?sayfa=1...' + scrapePageCount
                      }`}
                    </span>
                  )}
                  <button
                    onClick={handleScrape}
                    disabled={scraping || !scrapeUrl}
                    className="px-5 py-2 text-sm rounded-lg text-white font-medium disabled:opacity-50 flex items-center gap-2 whitespace-nowrap"
                    style={{ background: scraping ? '#334155' : 'linear-gradient(135deg, #00d4ff, #0099cc)' }}
                  >
                    {scraping ? (
                      <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    ) : (
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
                    )}
                    {scraping ? 'Scraping...' : 'Scrape Pages'}
                  </button>
                </div>
              </div>

              {scrapeProgress && (
                <div className="flex items-center gap-2 text-xs text-cyan-400">
                  <div className="w-3 h-3 border-2 border-cyan-400/30 border-t-cyan-400 rounded-full animate-spin" />
                  {scrapeProgress}
                </div>
              )}
              {scrapeMsg && (
                <p className={`text-xs ${scrapeMsg.includes('fail') || scrapeMsg.includes('Failed') ? 'text-red-400' : 'text-emerald-400'}`}>{scrapeMsg}</p>
              )}
            </div>
          </div>
        )}

        {showDetailPanel && viewMode === 'category_page' && (
          <div className="rounded-xl border border-purple-500/20 overflow-hidden" style={{ background: 'linear-gradient(135deg, rgba(168,85,247,0.05), rgba(168,85,247,0.02))' }}>
            <div className="p-4 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <svg className="w-4 h-4 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                  </svg>
                  <span className="text-sm font-medium text-purple-300">Get Product Details</span>
                  <span className="text-[10px] text-neutral-500">Step 2: Fetch detailed data for selected products</span>
                </div>
              </div>

              <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
                <div className="flex items-center gap-3 text-xs">
                  <span className="text-neutral-400">
                    <span className="text-white font-medium">{detailStats.total}</span> products
                  </span>
                  <span className="text-emerald-400">
                    <span className="font-medium">{detailStats.fetched}</span> detailed
                  </span>
                  <span className="text-amber-400">
                    <span className="font-medium">{detailStats.unfetched}</span> pending
                  </span>
                  <span className="text-cyan-400">
                    <span className="font-medium">{selectedForDetail.size}</span> selected
                  </span>
                </div>

                <div className="flex items-center gap-2 sm:ml-auto">
                  <button
                    onClick={selectAllForDetail}
                    className="px-3 py-1.5 text-xs rounded-lg border border-white/10 text-neutral-300 hover:bg-white/10 transition-colors flex items-center gap-1.5"
                  >
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                    </svg>
                    {selectedForDetail.size === detailStats.unfetched && detailStats.unfetched > 0 ? 'Deselect All' : `Select All (${detailStats.unfetched})`}
                  </button>
                  <button
                    onClick={handleFetchDetails}
                    disabled={detailFetching || selectedForDetail.size === 0}
                    className="px-4 py-1.5 text-xs rounded-lg text-white font-medium disabled:opacity-50 flex items-center gap-2 whitespace-nowrap"
                    style={{ background: detailFetching ? '#334155' : 'linear-gradient(135deg, #a855f7, #7c3aed)' }}
                  >
                    {detailFetching ? (
                      <div className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    ) : (
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
                    )}
                    {detailFetching ? 'Fetching...' : `Fetch Details (${selectedForDetail.size})`}
                  </button>
                </div>
              </div>

              {detailProgress && (
                <div className={`flex items-center gap-2 text-xs ${detailProgress.includes('failed') ? 'text-red-400' : detailProgress.includes('All details') ? 'text-emerald-400' : 'text-purple-400'}`}>
                  {detailFetching && <div className="w-3 h-3 border-2 border-purple-400/30 border-t-purple-400 rounded-full animate-spin" />}
                  {!detailFetching && detailProgress.includes('All details') && (
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
                  )}
                  {detailProgress}
                </div>
              )}
            </div>
          </div>
        )}

        <div className="flex items-center gap-1 p-1 rounded-xl bg-white/5 w-fit">
          <button
            onClick={() => setViewMode('my_products')}
            className={`px-4 py-2 text-sm rounded-lg font-medium transition-colors ${
              viewMode === 'my_products' ? 'bg-white/10 text-white shadow-sm' : 'text-neutral-400 hover:text-neutral-200'
            }`}
          >
            <span className="flex items-center gap-1.5">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" /></svg>
              My Products
            </span>
          </button>
          <button
            onClick={() => setViewMode('category_page')}
            className={`px-4 py-2 text-sm rounded-lg font-medium transition-colors ${
              viewMode === 'category_page' ? 'bg-white/10 text-white shadow-sm' : 'text-neutral-400 hover:text-neutral-200'
            }`}
          >
            <span className="flex items-center gap-1.5">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" /></svg>
              Category Page
            </span>
          </button>
        </div>

        {breadcrumbParts.length > 0 && (
          <div className="flex items-center gap-1.5 text-sm flex-wrap">
            <button onClick={() => setSelectedCategory('')} className="text-neutral-500 hover:text-cyan-400 transition-colors">All</button>
            {breadcrumbParts.map((bc, i) => (
              <span key={i} className="flex items-center gap-1.5">
                <svg className="w-3 h-3 text-neutral-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" /></svg>
                <button onClick={() => selectCategory(bc.path)}
                  className={`hover:text-cyan-400 transition-colors ${i === breadcrumbParts.length - 1 ? 'text-cyan-300 font-medium' : 'text-neutral-400'}`}>
                  {bc.name}
                </button>
              </span>
            ))}
            <button onClick={() => { setSelectedCategory(''); setExpandedCategories(new Set()); }} className="ml-2 text-neutral-600 hover:text-red-400 transition-colors">
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
            </button>
          </div>
        )}

        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
          <div className="relative flex-1 w-full sm:w-auto">
            <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              type="text" value={search} onChange={(e) => setSearch(e.target.value)}
              placeholder="Search products, brands, SKU..."
              className="w-full bg-black/30 border border-white/10 rounded-lg pl-10 pr-4 py-2.5 text-sm text-neutral-200 placeholder:text-neutral-600 focus:outline-none focus:border-cyan-500/50"
            />
          </div>
          {viewMode === 'my_products' ? (
            <select
              value={`${sortBy}:${sortDir}`}
              onChange={(e) => { const [s, d] = e.target.value.split(':'); setSortBy(s); setSortDir(d); }}
              className="bg-black/30 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-neutral-200 focus:outline-none focus:border-cyan-500/50"
            >
              <option value="created_at:desc">Newest First</option>
              <option value="created_at:asc">Oldest First</option>
              <option value="price:asc">Price: Low to High</option>
              <option value="price:desc">Price: High to Low</option>
              <option value="rating:desc">Highest Rated</option>
              <option value="product_name:asc">Name A-Z</option>
            </select>
          ) : (
            <select
              value={`${catSortBy}:${catSortDir}`}
              onChange={(e) => { const [s, d] = e.target.value.split(':'); setCatSortBy(s); setCatSortDir(d); }}
              className="bg-black/30 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-neutral-200 focus:outline-none focus:border-cyan-500/50"
            >
              <option value="position:asc">Marketplace Position</option>
              <option value="created_at:desc">Newest First</option>
              <option value="price:asc">Price: Low to High</option>
              <option value="price:desc">Price: High to Low</option>
              <option value="rating:desc">Highest Rated</option>
              <option value="name:asc">Name A-Z</option>
            </select>
          )}
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-1.5 text-center">
          <div className="rounded-lg border border-white/5 p-3" style={{ background: 'rgba(255,255,255,0.02)' }}>
            <div className="text-lg font-bold text-white">{dynamicStats.total.toLocaleString()}</div>
            <div className="text-xs text-neutral-500">Products</div>
          </div>
          <div className="rounded-lg border border-white/5 p-3" style={{ background: 'rgba(255,255,255,0.02)' }}>
            <div className="text-lg font-bold text-cyan-400">{formatPrice(dynamicStats.avgPrice)}</div>
            <div className="text-xs text-neutral-500">Avg Price</div>
          </div>
          <div className="rounded-lg border border-white/5 p-3" style={{ background: 'rgba(255,255,255,0.02)' }}>
            <div className="text-lg font-bold text-purple-400">{dynamicStats.brandCount}</div>
            <div className="text-xs text-neutral-500">Brands</div>
          </div>
          <div className="rounded-lg border border-white/5 p-3" style={{ background: 'rgba(255,255,255,0.02)' }}>
            {viewMode === 'category_page' ? (
              <>
                <div className="text-sm font-bold text-emerald-400">
                  {dynamicStats.lastScraped ? new Date(dynamicStats.lastScraped).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '-'}
                </div>
                <div className="text-xs text-neutral-500">Last Scraped</div>
              </>
            ) : (
              <>
                <div className="text-lg font-bold text-emerald-400">{dynamicStats.categoryCount}</div>
                <div className="text-xs text-neutral-500">Categories</div>
              </>
            )}
          </div>
        </div>

        {viewMode === 'category_page' && (
          <div className="flex flex-wrap items-end gap-2">
            <div className="flex-1 min-w-[140px]">
              <label className="text-[10px] text-neutral-500 uppercase tracking-wider mb-1 block">Brand</label>
              <select value={catBrand} onChange={e => setCatBrand(e.target.value)}
                className="w-full bg-black/30 border border-white/10 rounded-lg px-2.5 py-2 text-sm text-neutral-200 focus:outline-none focus:border-cyan-500/50">
                <option value="">All Brands</option>
                {(catFilterData?.brands || []).map(b => <option key={b} value={b}>{b}</option>)}
              </select>
            </div>
            <div className="flex-1 min-w-[140px]">
              <label className="text-[10px] text-neutral-500 uppercase tracking-wider mb-1 block">Seller</label>
              <select value={catSeller} onChange={e => setCatSeller(e.target.value)}
                className="w-full bg-black/30 border border-white/10 rounded-lg px-2.5 py-2 text-sm text-neutral-200 focus:outline-none focus:border-cyan-500/50">
                <option value="">All Sellers</option>
                {(catFilterData?.sellers || []).map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div className="min-w-[100px]">
              <label className="text-[10px] text-neutral-500 uppercase tracking-wider mb-1 block">Min Price</label>
              <input type="number" value={catMinPrice} onChange={e => setCatMinPrice(e.target.value)} placeholder="Min"
                className="w-full bg-black/30 border border-white/10 rounded-lg px-2.5 py-2 text-sm text-neutral-200 focus:outline-none focus:border-cyan-500/50" />
            </div>
            <div className="min-w-[100px]">
              <label className="text-[10px] text-neutral-500 uppercase tracking-wider mb-1 block">Max Price</label>
              <input type="number" value={catMaxPrice} onChange={e => setCatMaxPrice(e.target.value)} placeholder="Max"
                className="w-full bg-black/30 border border-white/10 rounded-lg px-2.5 py-2 text-sm text-neutral-200 focus:outline-none focus:border-cyan-500/50" />
            </div>
            <div className="min-w-[80px]">
              <label className="text-[10px] text-neutral-500 uppercase tracking-wider mb-1 block">Min Rating</label>
              <select value={catMinRating} onChange={e => setCatMinRating(e.target.value)}
                className="w-full bg-black/30 border border-white/10 rounded-lg px-2.5 py-2 text-sm text-neutral-200 focus:outline-none focus:border-cyan-500/50">
                <option value="">Any</option>
                <option value="4">4+</option>
                <option value="3">3+</option>
                <option value="2">2+</option>
              </select>
            </div>
            <div className="min-w-[100px]">
              <label className="text-[10px] text-neutral-500 uppercase tracking-wider mb-1 block">Sponsored</label>
              <select value={catSponsored} onChange={e => setCatSponsored(e.target.value as '' | 'true' | 'false')}
                className="w-full bg-black/30 border border-white/10 rounded-lg px-2.5 py-2 text-sm text-neutral-200 focus:outline-none focus:border-cyan-500/50">
                <option value="">All</option>
                <option value="true">Sponsored Only</option>
                <option value="false">Non-Sponsored</option>
              </select>
            </div>
            {(catBrand || catSeller || catMinPrice || catMaxPrice || catMinRating || catSponsored) && (
              <button
                onClick={() => { setCatBrand(''); setCatSeller(''); setCatMinPrice(''); setCatMaxPrice(''); setCatMinRating(''); setCatSponsored(''); }}
                className="text-xs text-neutral-400 hover:text-red-400 px-2 py-2 transition-colors whitespace-nowrap"
              >
                Clear Filters
              </button>
            )}
          </div>
        )}

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : viewMode === 'my_products' ? (
          currentProducts.length > 0 ? (
            <>
              <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
                {currentProducts.map(renderProductCard)}
              </div>
              <Pagination />
            </>
          ) : (
            <EmptyState viewMode={viewMode} hasFilters={!!(selectedCategory || selectedBrand || search)} />
          )
        ) : (
          currentCatProducts.length > 0 ? (
            <>
              <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
                {currentCatProducts.map(renderCatProductCard)}
              </div>
              <Pagination />
            </>
          ) : (
            <EmptyState viewMode={viewMode} hasFilters={!!(selectedCategory || search)} />
          )
        )}
      </main>

      {selectedProduct && createPortal(
        <ProductDetailPanel product={selectedProduct} onClose={() => setSelectedProduct(null)} formatPrice={formatPrice} selectCategory={(cat) => { selectCategory(cat); setSelectedProduct(null); }} />,
        document.body
      )}

      {selectedCatProduct && createPortal(
        <CatProductDetailPanel product={selectedCatProduct} onClose={() => setSelectedCatProduct(null)} formatPrice={formatPrice} />,
        document.body
      )}

      {showMobileFilters && createPortal(
        <>
          <div className="fixed inset-0 bg-black/60 z-[9996]" onClick={() => setShowMobileFilters(false)} />
          <div className="fixed top-0 left-0 h-full w-80 z-[9997] overflow-y-auto border-r border-white/10 shadow-2xl p-4"
            style={{ background: 'linear-gradient(180deg, #141619 0%, #0e0f11 100%)' }}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-base font-semibold text-white">Filters</h3>
              <button onClick={() => setShowMobileFilters(false)} className="p-1.5 rounded-lg hover:bg-white/10 text-neutral-400">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>
            <FilterSidebar />
          </div>
        </>,
        document.body
      )}
    </div>
  );
}


function EmptyState({ viewMode, hasFilters }: { viewMode: ViewMode; hasFilters: boolean }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="w-16 h-16 rounded-2xl bg-white/5 flex items-center justify-center mb-4">
        <svg className="w-8 h-8 text-neutral-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
        </svg>
      </div>
      <h3 className="text-lg font-medium text-neutral-300 mb-2">
        {viewMode === 'category_page' ? 'No Scraped Products' : 'No Products Found'}
      </h3>
      <p className="text-sm text-neutral-500 max-w-md">
        {viewMode === 'category_page'
          ? hasFilters
            ? 'No scraped products match this category. Use "Scrape New" to scrape a category page first.'
            : 'Use "Scrape New" to scrape a marketplace category page. Products will appear here in their marketplace order.'
          : hasFilters
            ? 'Try adjusting your filters or search to find products.'
            : 'Use the "Scrape New" button to import products from marketplace category pages.'}
      </p>
    </div>
  );
}


function ProductDetailPanel({ product, onClose, formatPrice, selectCategory }: {
  product: StoreProduct;
  onClose: () => void;
  formatPrice: (p: number | null | undefined) => string;
  selectCategory: (cat: string) => void;
}) {
  return (
    <>
      <div className="fixed inset-0 bg-black/60 z-[9998]" onClick={onClose} />
      <div className="fixed top-0 right-0 h-full w-full max-w-lg z-[9999] overflow-y-auto border-l border-white/10 shadow-2xl"
        style={{ background: 'linear-gradient(180deg, #141619 0%, #0e0f11 100%)' }}>
        <div className="sticky top-0 z-10 flex items-center justify-between p-4 border-b border-white/10" style={{ background: 'rgba(20,22,25,0.95)', backdropFilter: 'blur(8px)' }}>
          <div className="flex items-center gap-2">
            <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${
              product.platform === 'hepsiburada' ? 'bg-orange-500/20 text-orange-400' :
              product.platform === 'trendyol' ? 'bg-purple-500/20 text-purple-400' :
              'bg-blue-500/20 text-blue-400'
            }`}>
              {product.platform === 'hepsiburada' ? 'HB' : product.platform === 'trendyol' ? 'TY' : 'WEB'}
            </span>
            <h3 className="text-base font-semibold text-white truncate">Product Details</h3>
          </div>
          <div className="flex items-center gap-2">
            <a href={product.source_url} target="_blank" rel="noopener noreferrer" className="p-1.5 rounded-lg hover:bg-white/10 text-neutral-400">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
            </a>
            <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-white/10 text-neutral-400">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
            </button>
          </div>
        </div>

        <div className="p-4 space-y-4">
          {product.image_url && (
            <div className="rounded-lg bg-white/5 p-4 flex items-center justify-center">
              <img src={product.image_url} alt="" className="max-h-64 object-contain" />
            </div>
          )}
          <div>
            {product.brand && <div className="text-xs text-cyan-400 font-medium uppercase mb-1">{product.brand}</div>}
            <h4 className="text-base font-medium text-white leading-snug">{product.product_name}</h4>
          </div>
          {product.category && (
            <div>
              <div className="text-xs text-neutral-500 mb-1">Category</div>
              <div className="flex items-center gap-1 flex-wrap">
                {product.category.split(' > ').map((part, i, arr) => (
                  <span key={i} className="flex items-center gap-1">
                    {i > 0 && <svg className="w-2.5 h-2.5 text-neutral-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" /></svg>}
                    <button onClick={() => selectCategory(arr.slice(0, i + 1).join(' > '))} className="text-xs text-neutral-400 hover:text-cyan-400 transition-colors">{part.trim()}</button>
                  </span>
                ))}
              </div>
            </div>
          )}
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-lg bg-white/5 p-3">
              <div className="text-xs text-neutral-500 mb-1">Price</div>
              <div className="text-lg font-bold text-white">{formatPrice(product.price)}</div>
            </div>
            <div className="rounded-lg bg-white/5 p-3">
              <div className="text-xs text-neutral-500 mb-1">Rating</div>
              <div className="text-lg font-bold text-white flex items-center gap-1">
                {product.rating || '-'}
                {product.rating && <svg className="w-4 h-4 text-amber-400 fill-current" viewBox="0 0 20 20"><path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" /></svg>}
              </div>
              <div className="text-xs text-neutral-500">{product.review_count ?? 0} reviews</div>
            </div>
          </div>
          <div className="space-y-2 text-sm">
            {product.sku && <div className="flex justify-between py-1.5 border-b border-white/5"><span className="text-neutral-500">SKU</span><span className="text-white font-mono text-xs">{product.sku}</span></div>}
            {product.barcode && <div className="flex justify-between py-1.5 border-b border-white/5"><span className="text-neutral-500">Barcode</span><span className="text-white font-mono text-xs">{product.barcode}</span></div>}
            {product.seller_name && <div className="flex justify-between py-1.5 border-b border-white/5"><span className="text-neutral-500">Seller</span><span className="text-white">{product.seller_name}</span></div>}
            {product.availability && <div className="flex justify-between py-1.5 border-b border-white/5"><span className="text-neutral-500">Availability</span><span className={product.availability.toLowerCase().includes('instock') || product.availability.toLowerCase().includes('in stock') ? 'text-emerald-400' : 'text-red-400'}>{product.availability}</span></div>}
            {product.shipping_info && <div className="flex justify-between py-1.5 border-b border-white/5"><span className="text-neutral-500">Shipping</span><span className="text-white">{product.shipping_info.cost} {product.shipping_info.currency}</span></div>}
            {product.return_policy && <div className="flex justify-between py-1.5 border-b border-white/5"><span className="text-neutral-500">Return Policy</span><span className="text-white">{product.return_policy.days} days {product.return_policy.free_return ? '(Free)' : ''}</span></div>}
          </div>
          {product.description && (
            <div>
              <div className="text-xs text-neutral-500 mb-1">Description</div>
              <p className="text-xs text-neutral-300 leading-relaxed max-h-32 overflow-y-auto">{product.description}</p>
            </div>
          )}
          {product.product_specs && Object.keys(product.product_specs).length > 0 && (
            <div>
              <div className="text-xs text-neutral-500 mb-1">Specifications</div>
              <div className="space-y-1">
                {Object.entries(product.product_specs).map(([k, v]) => (
                  <div key={k} className="flex justify-between text-xs py-0.5"><span className="text-neutral-500">{k}</span><span className="text-neutral-300">{v}</span></div>
                ))}
              </div>
            </div>
          )}
          {product.reviews && product.reviews.length > 0 && (
            <div>
              <div className="text-xs text-neutral-500 mb-1">Reviews ({product.reviews.length})</div>
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {product.reviews.slice(0, 5).map((r, i) => (
                  <div key={i} className="rounded-lg bg-white/5 p-2 text-xs">
                    <div className="flex items-center gap-1 mb-1">
                      {r.rating && <span className="text-amber-400">{r.rating}★</span>}
                      {r.author && <span className="text-neutral-400">{r.author}</span>}
                    </div>
                    <p className="text-neutral-300 line-clamp-3">{r.text}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}


function CatProductDetailPanel({ product, onClose, formatPrice }: {
  product: CategoryProductItem;
  onClose: () => void;
  formatPrice: (p: number | null | undefined) => string;
}) {
  const detail = product.detail_data || {};
  return (
    <>
      <div className="fixed inset-0 bg-black/60 z-[9998]" onClick={onClose} />
      <div className="fixed top-0 right-0 h-full w-full max-w-lg z-[9999] overflow-y-auto border-l border-white/10 shadow-2xl"
        style={{ background: 'linear-gradient(180deg, #141619 0%, #0e0f11 100%)' }}>
        <div className="sticky top-0 z-10 flex items-center justify-between p-4 border-b border-white/10" style={{ background: 'rgba(20,22,25,0.95)', backdropFilter: 'blur(8px)' }}>
          <div className="flex items-center gap-2">
            <span className="text-xs px-1.5 py-0.5 rounded font-medium bg-white/10 text-neutral-300 font-mono">#{product.position}</span>
            <h3 className="text-base font-semibold text-white truncate">Category Product</h3>
            {product.detail_fetched && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400">Detailed</span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {product.url && (
              <a href={product.url} target="_blank" rel="noopener noreferrer" className="p-1.5 rounded-lg hover:bg-white/10 text-neutral-400">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
              </a>
            )}
            <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-white/10 text-neutral-400">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
            </button>
          </div>
        </div>

        <div className="p-4 space-y-4">
          {product.image_url && (
            <div className="rounded-lg bg-white/5 p-4 flex items-center justify-center">
              <img src={product.image_url} alt="" className="max-h-64 object-contain" />
            </div>
          )}
          <div>
            {product.brand && <div className="text-xs text-cyan-400 font-medium uppercase mb-1">{product.brand}</div>}
            <h4 className="text-base font-medium text-white leading-snug">{product.name}</h4>
          </div>
          <div className="grid grid-cols-3 gap-2">
            <div className="rounded-lg bg-white/5 p-3 text-center">
              <div className="text-xs text-neutral-500 mb-1">Price</div>
              <div className="text-base font-bold text-white">{formatPrice(product.price)}</div>
              {product.original_price && product.original_price > (product.price || 0) && (
                <div className="text-xs text-neutral-500 line-through">{formatPrice(product.original_price)}</div>
              )}
            </div>
            <div className="rounded-lg bg-white/5 p-3 text-center">
              <div className="text-xs text-neutral-500 mb-1">Position</div>
              <div className="text-base font-bold text-white">#{product.position}</div>
              <div className="text-xs text-neutral-500">Page {product.page_number}</div>
            </div>
            <div className="rounded-lg bg-white/5 p-3 text-center">
              <div className="text-xs text-neutral-500 mb-1">Rating</div>
              <div className="text-base font-bold text-white flex items-center justify-center gap-1">
                {product.rating || '-'}
                {product.rating && <svg className="w-3 h-3 text-amber-400 fill-current" viewBox="0 0 20 20"><path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" /></svg>}
              </div>
              <div className="text-xs text-neutral-500">{product.review_count ?? 0}</div>
            </div>
          </div>
          <div className="space-y-2 text-sm">
            {product.is_sponsored && (
              <div className="flex justify-between py-1.5 border-b border-white/5">
                <span className="text-neutral-500">Type</span>
                <span className="text-amber-400 font-medium">Sponsored Ad</span>
              </div>
            )}
            {product.seller_name && (
              <div className="flex justify-between py-1.5 border-b border-white/5">
                <span className="text-neutral-500">Seller</span>
                <span className="text-white">{product.seller_name}</span>
              </div>
            )}
            {product.sku && (
              <div className="flex justify-between py-1.5 border-b border-white/5">
                <span className="text-neutral-500">SKU</span>
                <span className="text-white font-mono text-xs">{product.sku}</span>
              </div>
            )}
            {product.barcode && (
              <div className="flex justify-between py-1.5 border-b border-white/5">
                <span className="text-neutral-500">Barcode</span>
                <span className="text-white font-mono text-xs">{product.barcode}</span>
              </div>
            )}
            {product.stock_status && (
              <div className="flex justify-between py-1.5 border-b border-white/5">
                <span className="text-neutral-500">Stock</span>
                <span className={product.stock_status === 'inStock' ? 'text-emerald-400' : 'text-orange-400'}>{product.stock_status}</span>
              </div>
            )}
            {product.shipping_type && (
              <div className="flex justify-between py-1.5 border-b border-white/5">
                <span className="text-neutral-500">Shipping</span>
                <span className="text-white">{product.shipping_type}</span>
              </div>
            )}
            {product.campaign_text && (
              <div className="flex justify-between py-1.5 border-b border-white/5">
                <span className="text-neutral-500">Campaign</span>
                <span className="text-emerald-400">{product.campaign_text}</span>
              </div>
            )}
            {product.discount_percentage && (
              <div className="flex justify-between py-1.5 border-b border-white/5">
                <span className="text-neutral-500">Discount</span>
                <span className="text-emerald-400">-{product.discount_percentage}%</span>
              </div>
            )}
          </div>
          {product.category_path && (
            <div>
              <div className="text-xs text-neutral-500 mb-1 font-medium">Category Path</div>
              <p className="text-xs text-neutral-300">{product.category_path}</p>
            </div>
          )}
          {product.seller_list && product.seller_list.length > 0 && (
            <div>
              <div className="text-xs text-neutral-500 mb-2 font-medium">All Sellers ({product.seller_list.length})</div>
              <div className="space-y-1">
                {product.seller_list.map((s: any, i: number) => (
                  <div key={i} className="flex items-center justify-between text-xs py-1 px-2 rounded bg-white/5">
                    <span className="text-white">{s.name}</span>
                    {s.id && <span className="text-neutral-500 font-mono text-[10px]">ID: {s.id}</span>}
                  </div>
                ))}
              </div>
            </div>
          )}
          {product.description && (
            <div>
              <div className="text-xs text-neutral-500 mb-1 font-medium">Description</div>
              <p className="text-xs text-neutral-300 leading-relaxed max-h-40 overflow-y-auto whitespace-pre-line">{product.description}</p>
            </div>
          )}
          {product.specs && Object.keys(product.specs).length > 0 && (
            <div>
              <div className="text-xs text-neutral-500 mb-2 font-medium">Specifications</div>
              <div className="space-y-1">
                {Object.entries(product.specs).map(([k, v]) => (
                  <div key={k} className="flex justify-between text-xs py-1 px-2 rounded bg-white/5">
                    <span className="text-neutral-400">{k}</span>
                    <span className="text-white text-right max-w-[60%]">{String(v)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          {detail && Object.keys(detail).length > 0 && !product.specs && (
            <div>
              <div className="text-xs text-neutral-500 mb-2 font-medium">Additional Details</div>
              {detail.description && !product.description && (
                <div className="mb-2">
                  <div className="text-xs text-neutral-500 mb-1">Description</div>
                  <p className="text-xs text-neutral-300 leading-relaxed max-h-32 overflow-y-auto">{detail.description}</p>
                </div>
              )}
              {detail.category && !product.category_path && (
                <div className="mb-2">
                  <div className="text-xs text-neutral-500 mb-1">Category</div>
                  <p className="text-xs text-neutral-300">{detail.category}</p>
                </div>
              )}
              {detail.product_specs && Object.keys(detail.product_specs).length > 0 && (
                <div className="mb-2">
                  <div className="text-xs text-neutral-500 mb-1">Specifications</div>
                  <div className="space-y-1">
                    {Object.entries(detail.product_specs).map(([k, v]) => (
                      <div key={k} className="flex justify-between text-xs py-0.5"><span className="text-neutral-500">{k}</span><span className="text-neutral-300">{String(v)}</span></div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
