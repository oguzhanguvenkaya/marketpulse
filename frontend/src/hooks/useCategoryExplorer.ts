import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { toast } from 'sonner';
import {
  getStoreProducts,
  getStoreProductFilters,
  getStoreCategoryTree,
  getCategoryProductsByCategory,
  getCategoryPageFilters,
  scrapeCategoryPage,
  fetchCategoryProductDetail,
  getCategoryFetchStatus,
  deleteCategoryProduct,
  deleteCategoryProductsBulk,
  type StoreProduct,
  type StoreProductFilters,
  type StoreProductListResponse,
  type CategoryTreeNode,
  type CategoryProductItem,
  type CategoryProductListResponse,
  type CategoryFilterData,
} from '../services/api';

export type Platform = '' | 'hepsiburada' | 'trendyol' | 'web';
export type ViewMode = 'my_products' | 'category_page';

const SS_KEY = 'catExplorer';
function ssGet(key: string): string { try { return sessionStorage.getItem(`${SS_KEY}_${key}`) || ''; } catch { return ''; } }
function ssSet(key: string, val: string) { try { sessionStorage.setItem(`${SS_KEY}_${key}`, val); } catch {} }
function ssGetJson<T>(key: string, fallback: T): T { try { const v = sessionStorage.getItem(`${SS_KEY}_${key}`); return v ? JSON.parse(v) : fallback; } catch { return fallback; } }
function ssSetJson(key: string, val: unknown) { try { sessionStorage.setItem(`${SS_KEY}_${key}`, JSON.stringify(val)); } catch {} }

export function useCategoryExplorer() {
  const [searchParams, setSearchParams] = useSearchParams();

  const initParam = (key: string, def: string) => searchParams.get(key) || def;

  const [platform, setPlatform] = useState<Platform>((initParam('platform', '') as Platform));
  const [viewMode, setViewMode] = useState<ViewMode>((initParam('view', 'my_products') as ViewMode));
  const [data, setData] = useState<StoreProductListResponse | null>(null);
  const [catData, setCatData] = useState<CategoryProductListResponse | null>(null);
  const [filters, setFilters] = useState<StoreProductFilters | null>(null);
  const [categoryTree, setCategoryTree] = useState<CategoryTreeNode[]>([]);
  const [loading, setLoading] = useState(true);

  const [search, setSearch] = useState(initParam('search', ''));
  const [selectedCategory, setSelectedCategory] = useState(initParam('category', ''));
  const [selectedBrand, setSelectedBrand] = useState(initParam('brand', ''));
  const [minPrice, setMinPrice] = useState(initParam('minPrice', ''));
  const [maxPrice, setMaxPrice] = useState(initParam('maxPrice', ''));
  const [minRating, setMinRating] = useState(initParam('minRating', ''));
  const [sortBy, setSortBy] = useState(initParam('sortBy', 'created_at'));
  const [sortDir, setSortDir] = useState(initParam('sortDir', 'desc'));
  const [page, setPage] = useState(parseInt(initParam('page', '1'), 10) || 1);
  const [pageSize] = useState(50);

  const [selectedProduct, setSelectedProduct] = useState<StoreProduct | null>(null);
  const [selectedCatProduct, setSelectedCatProduct] = useState<CategoryProductItem | null>(null);
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(() => {
    return new Set(ssGetJson<string[]>('expandedCategories', []));
  });
  const [showScraper, setShowScraper] = useState(() => ssGet('showScraper') === 'true');
  const [scrapeUrl, setScrapeUrl] = useState(() => ssGet('scrapeUrl'));
  const [scrapePageCount, setScrapePageCount] = useState(() => parseInt(ssGet('scrapePageCount') || '1', 10) || 1);
  const [scraping, setScraping] = useState(false);
  const [scrapeMsg, setScrapeMsg] = useState('');
  const [scrapeProgress, setScrapeProgress] = useState('');
  const [scrapeSessionId, setScrapeSessionId] = useState<string | null>(() => ssGet('scrapeSessionId') || null);
  const [showMobileFilters, setShowMobileFilters] = useState(false);

  const [catFilterData, setCatFilterData] = useState<CategoryFilterData | null>(null);
  const [catBrand, setCatBrand] = useState(initParam('catBrand', ''));
  const [catSeller, setCatSeller] = useState(initParam('catSeller', ''));
  const [catMinPrice, setCatMinPrice] = useState(initParam('catMinPrice', ''));
  const [catMaxPrice, setCatMaxPrice] = useState(initParam('catMaxPrice', ''));
  const [catMinRating, setCatMinRating] = useState(initParam('catMinRating', ''));
  const [catSponsored, setCatSponsored] = useState<'' | 'true' | 'false'>((initParam('catSponsored', '') as '' | 'true' | 'false'));
  const [catSortBy, setCatSortBy] = useState(initParam('catSortBy', 'position'));
  const [catSortDir, setCatSortDir] = useState(initParam('catSortDir', 'asc'));

  const [showDetailPanel, setShowDetailPanel] = useState(() => ssGet('showDetailPanel') === 'true');
  const [selectedForDetail, setSelectedForDetail] = useState<Set<number>>(() => {
    return new Set(ssGetJson<number[]>('selectedForDetail', []));
  });
  const [detailFetching, setDetailFetching] = useState(false);
  const [detailProgress, setDetailProgress] = useState('');
  const detailPollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const [confirmAction, setConfirmAction] = useState<{
    type: 'delete-single' | 'delete-bulk';
    productId?: number;
    message: string;
  } | null>(null);

  // Sync state to URL params
  useEffect(() => {
    const params: Record<string, string> = {};
    if (platform) params.platform = platform;
    if (viewMode !== 'my_products') params.view = viewMode;
    if (search) params.search = search;
    if (selectedCategory) params.category = selectedCategory;
    if (selectedBrand) params.brand = selectedBrand;
    if (minPrice) params.minPrice = minPrice;
    if (maxPrice) params.maxPrice = maxPrice;
    if (minRating) params.minRating = minRating;
    if (sortBy !== 'created_at') params.sortBy = sortBy;
    if (sortDir !== 'desc') params.sortDir = sortDir;
    if (page > 1) params.page = String(page);
    if (catBrand) params.catBrand = catBrand;
    if (catSeller) params.catSeller = catSeller;
    if (catMinPrice) params.catMinPrice = catMinPrice;
    if (catMaxPrice) params.catMaxPrice = catMaxPrice;
    if (catMinRating) params.catMinRating = catMinRating;
    if (catSponsored) params.catSponsored = catSponsored;
    if (catSortBy !== 'position') params.catSortBy = catSortBy;
    if (catSortDir !== 'asc') params.catSortDir = catSortDir;
    setSearchParams(params, { replace: true });
  }, [platform, viewMode, search, selectedCategory, selectedBrand, minPrice, maxPrice, minRating, sortBy, sortDir, page, catBrand, catSeller, catMinPrice, catMaxPrice, catMinRating, catSponsored, catSortBy, catSortDir]);

  // Session storage persistence
  useEffect(() => {
    ssSet('showScraper', showScraper ? 'true' : 'false');
  }, [showScraper]);
  useEffect(() => { ssSet('scrapeUrl', scrapeUrl); }, [scrapeUrl]);
  useEffect(() => { ssSet('scrapePageCount', String(scrapePageCount)); }, [scrapePageCount]);
  useEffect(() => { ssSet('scrapeSessionId', scrapeSessionId || ''); }, [scrapeSessionId]);
  useEffect(() => { ssSet('showDetailPanel', showDetailPanel ? 'true' : 'false'); }, [showDetailPanel]);
  useEffect(() => { ssSetJson('selectedForDetail', Array.from(selectedForDetail)); }, [selectedForDetail]);
  useEffect(() => { ssSetJson('expandedCategories', Array.from(expandedCategories)); }, [expandedCategories]);

  // Data fetching callbacks
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

  // Data fetching effects
  useEffect(() => {
    if (viewMode === 'my_products') fetchMyProducts();
    else fetchCatProducts();
  }, [viewMode, fetchMyProducts, fetchCatProducts]);

  useEffect(() => { fetchFilters(); }, [fetchFilters]);

  useEffect(() => {
    if (viewMode === 'category_page') fetchCatFilterData();
  }, [viewMode, fetchCatFilterData]);

  // Reset page on filter changes
  useEffect(() => {
    setPage(1);
  }, [platform, search, selectedCategory, selectedBrand, minPrice, maxPrice, minRating, sortBy, sortDir, viewMode, catBrand, catSeller, catMinPrice, catMaxPrice, catMinRating, catSponsored, catSortBy, catSortDir]);

  // Category URL map
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

  // Auto-fill scrape URL from selected category
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

  // Cleanup detail poll on unmount
  useEffect(() => {
    return () => {
      if (detailPollRef.current) clearInterval(detailPollRef.current);
    };
  }, []);

  // Handlers
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

  const selectAllProducts = () => {
    const products = catData?.products || [];
    if (products.length === 0) return;
    if (selectedForDetail.size === products.length) {
      setSelectedForDetail(new Set());
    } else {
      setSelectedForDetail(new Set(products.map(p => p.id)));
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
              fetchCatFilterData();
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

  const handleDeleteProductRequest = (productId: number) => {
    setConfirmAction({
      type: 'delete-single',
      productId,
      message: 'Bu urunu silmek istediginizden emin misiniz?',
    });
  };

  const handleBulkDeleteRequest = () => {
    if (selectedForDetail.size === 0) return;
    setConfirmAction({
      type: 'delete-bulk',
      message: `${selectedForDetail.size} secili urunu silmek istediginizden emin misiniz?`,
    });
  };

  const handleConfirmAction = async () => {
    if (!confirmAction) return;
    const action = confirmAction;
    setConfirmAction(null);

    if (action.type === 'delete-single' && action.productId !== undefined) {
      try {
        await deleteCategoryProduct(action.productId);
        fetchCatProducts();
        fetchCatFilterData();
        if (selectedCatProduct?.id === action.productId) setSelectedCatProduct(null);
        toast.success('Urun silindi');
      } catch (err: any) {
        toast.error(err?.response?.data?.detail || 'Delete failed');
      }
    } else if (action.type === 'delete-bulk') {
      try {
        await deleteCategoryProductsBulk(Array.from(selectedForDetail));
        setSelectedForDetail(new Set());
        fetchCatProducts();
        fetchCatFilterData();
        toast.success('Urunler silindi');
      } catch (err: any) {
        toast.error(err?.response?.data?.detail || 'Bulk delete failed');
      }
    }
  };

  const handleCancelAction = () => {
    setConfirmAction(null);
  };

  const formatPrice = (price: number | null | undefined) => {
    if (!price) return '-';
    return new Intl.NumberFormat('tr-TR', { style: 'currency', currency: 'TRY', minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(price);
  };

  // Memos
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

  return {
    // State
    platform,
    viewMode,
    data,
    catData,
    filters,
    categoryTree,
    loading,
    search,
    selectedCategory,
    selectedBrand,
    minPrice,
    maxPrice,
    minRating,
    sortBy,
    sortDir,
    page,
    pageSize,
    selectedProduct,
    selectedCatProduct,
    expandedCategories,
    showScraper,
    scrapeUrl,
    scrapePageCount,
    scraping,
    scrapeMsg,
    scrapeProgress,
    scrapeSessionId,
    showMobileFilters,
    catFilterData,
    catBrand,
    catSeller,
    catMinPrice,
    catMaxPrice,
    catMinRating,
    catSponsored,
    catSortBy,
    catSortDir,
    showDetailPanel,
    selectedForDetail,
    detailFetching,
    detailProgress,

    // Setters
    setPlatform,
    setViewMode,
    setSearch,
    setSelectedCategory,
    setSelectedBrand,
    setMinPrice,
    setMaxPrice,
    setMinRating,
    setSortBy,
    setSortDir,
    setPage,
    setSelectedProduct,
    setSelectedCatProduct,
    setExpandedCategories,
    setShowScraper,
    setScrapeUrl,
    setScrapePageCount,
    setShowMobileFilters,
    setCatBrand,
    setCatSeller,
    setCatMinPrice,
    setCatMaxPrice,
    setCatMinRating,
    setCatSponsored,
    setCatSortBy,
    setCatSortDir,
    setShowDetailPanel,
    setSelectedForDetail,

    // Handlers
    handlePlatformChange,
    toggleCategory,
    selectCategory,
    handleScrape,
    toggleProductSelection,
    selectAllForDetail,
    selectAllProducts,
    handleFetchDetails,
    confirmAction,
    handleDeleteProductRequest,
    handleBulkDeleteRequest,
    handleConfirmAction,
    handleCancelAction,
    formatPrice,

    // Memos / derived
    breadcrumbParts,
    platformStats,
    dynamicStats,
    detailStats,
    currentProducts,
    currentCatProducts,
    currentTotal,
    currentTotalPages,
  };
}

export type UseCategoryExplorerReturn = ReturnType<typeof useCategoryExplorer>;
