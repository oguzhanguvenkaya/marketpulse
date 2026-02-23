import { useCallback, useEffect, useRef, useState } from 'react';
import {
  getMonitoredProducts,
  getMonitoredProductDetail,
  addMonitoredProducts,
  deleteMonitoredProduct,
  deleteAllMonitoredProducts,
  deleteInactiveMonitoredProducts,
  startFetchTask,
  stopFetchTask,
  getFetchTaskStatus,
  fetchSingleProduct,
  exportPriceMonitorData,
  getBrands,
  getLastInactiveSkus,
} from '../services/api';
import type { FetchType } from '../services/api';
import type {
  MonitoredProduct,
  SellerSnapshot,
  BulkProductInput,
} from '../services/api';

type Platform = 'hepsiburada' | 'trendyol';
const PAGE_SIZE = 100;
const SEARCH_DEBOUNCE_MS = 400;
const FETCH_STATUS_POLL_MS = 2000;

export { PAGE_SIZE };

export function usePriceMonitor() {
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
  const [campaignAlertOnly, setCampaignAlertOnly] = useState(false);
  const [searchInput, setSearchInput] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [lastInactiveCount, setLastInactiveCount] = useState(0);
  const [showFetchMenu, setShowFetchMenu] = useState(false);
  const [currentFetchType, setCurrentFetchType] = useState<FetchType>('active');
  const [showDeleteModal, setShowDeleteModal] = useState<'all' | 'inactive' | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [totalProducts, setTotalProducts] = useState(0);
  const [activeTotalCount, setActiveTotalCount] = useState(0);
  const [inactiveTotalCount, setInactiveTotalCount] = useState(0);
  const [currentOffset, setCurrentOffset] = useState(0);
  const currentOffsetRef = useRef(0);
  const productLoadAbortRef = useRef<AbortController | null>(null);
  const firstFilterRunRef = useRef(true);
  const mountedPlatformRef = useRef<Platform | null>(null);
  const terminalRefreshTaskIdsRef = useRef<Set<string>>(new Set());

  const activeProducts = products.filter(p => p.is_active !== false);
  const inactiveProducts = products.filter(p => p.is_active === false);

  useEffect(() => {
    currentOffsetRef.current = currentOffset;
  }, [currentOffset]);

  useEffect(() => {
    const handleClickOutside = () => {
      setShowFetchMenu(false);
      setShowExportMenu(false);
    };
    document.addEventListener('click', handleClickOutside);
    return () => document.removeEventListener('click', handleClickOutside);
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setSearchQuery(searchInput.trim());
    }, SEARCH_DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [searchInput]);

  useEffect(() => {
    return () => {
      productLoadAbortRef.current?.abort();
    };
  }, []);

  const loadLastInactive = useCallback(async () => {
    try {
      const data = await getLastInactiveSkus(platform);
      setLastInactiveCount(data.count);
    } catch (e) {
      console.error('Error loading last inactive:', e);
    }
  }, [platform]);

  const loadBrands = useCallback(async () => {
    try {
      const data = await getBrands(platform);
      setBrands(data.brands);
    } catch (e) {
      console.error('Error loading brands:', e);
    }
  }, [platform]);

  const isAbortError = (error: unknown) => {
    if (!error || typeof error !== 'object') return false;
    const err = error as { name?: string; code?: string };
    return err.name === 'CanceledError' || err.name === 'AbortError' || err.code === 'ERR_CANCELED';
  };

  const loadProducts = useCallback(async (offsetOverride?: number) => {
    const useOffset = offsetOverride !== undefined ? offsetOverride : currentOffsetRef.current;
    productLoadAbortRef.current?.abort();
    const controller = new AbortController();
    productLoadAbortRef.current = controller;

    try {
      setLoading(true);
      setSelectedProduct(null);
      setSellers([]);

      const params: Record<string, string | number | boolean> = { limit: PAGE_SIZE, offset: useOffset };
      if (selectedBrand) params.brand = selectedBrand;
      if (priceAlertOnly) params.price_alert_only = true;
      if (campaignAlertOnly) params.campaign_alert_only = true;
      if (searchQuery) params.search = searchQuery;

      const data = await getMonitoredProducts(platform, params, { signal: controller.signal });
      if (productLoadAbortRef.current !== controller) {
        return;
      }

      setProducts(data.products);
      setTotalProducts(data.total);
      setActiveTotalCount(data.active_count ?? data.products.filter((p) => p.is_active !== false).length);
      setInactiveTotalCount(data.inactive_count ?? data.products.filter((p) => p.is_active === false).length);
    } catch (e) {
      if (!isAbortError(e)) {
        console.error('Error loading products:', e);
      }
    }
    finally {
      if (productLoadAbortRef.current === controller) {
        setLoading(false);
      }
    }
  }, [campaignAlertOnly, platform, priceAlertOnly, searchQuery, selectedBrand]);

  useEffect(() => {
    if (mountedPlatformRef.current === platform) {
      return;
    }
    mountedPlatformRef.current = platform;

    setCurrentOffset(0);
    currentOffsetRef.current = 0;
    void Promise.all([loadProducts(0), loadBrands(), loadLastInactive()]);
  }, [platform, loadBrands, loadLastInactive, loadProducts]);

  useEffect(() => {
    if (firstFilterRunRef.current) {
      firstFilterRunRef.current = false;
      return;
    }

    setCurrentOffset(0);
    currentOffsetRef.current = 0;
    void loadProducts(0);
  }, [selectedBrand, priceAlertOnly, campaignAlertOnly, searchQuery, loadProducts]);

  useEffect(() => {
    if (!fetchTaskId) {
      return;
    }

    let interval: ReturnType<typeof setInterval> | null = null;
    let isChecking = false;

    interval = setInterval(async () => {
      if (isChecking) {
        return;
      }
      isChecking = true;
      try {
        const status = await getFetchTaskStatus(fetchTaskId);
        setFetchStatus(status.status);
        setFetchProgress({ completed: status.completed_products, total: status.total_products });

        if (status.status === 'completed' || status.status === 'stopped' || status.status === 'failed') {
          if (!terminalRefreshTaskIdsRef.current.has(fetchTaskId)) {
            terminalRefreshTaskIdsRef.current.add(fetchTaskId);
            await Promise.all([loadProducts(), loadLastInactive()]);
          }
          setFetchTaskId(null);
        }
      } catch (e) {
        console.error('Error checking fetch status:', e);
      } finally {
        isChecking = false;
      }
    }, FETCH_STATUS_POLL_MS);

    return () => {
      if (interval) {
        clearInterval(interval);
      }
    };
  }, [fetchTaskId, loadLastInactive, loadProducts]);

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
      void loadProducts();
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : 'Unknown error';
      alert('JSON parse error: ' + message);
    } finally {
      setImportLoading(false);
    }
  };

  const handleFetchAll = async (fetchType: FetchType = 'active') => {
    try {
      setCurrentFetchType(fetchType);
      setShowFetchMenu(false);
      const result = await startFetchTask(platform, fetchType);
      terminalRefreshTaskIdsRef.current.delete(result.task_id);
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
        void handleProductClick(selectedProduct);
      }
      void Promise.all([loadProducts(), loadLastInactive()]);
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
      void loadProducts();
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

  const handleBulkDelete = async () => {
    if (!showDeleteModal) return;
    try {
      setDeleteLoading(true);
      let result;
      if (showDeleteModal === 'all') {
        result = await deleteAllMonitoredProducts(platform);
      } else {
        result = await deleteInactiveMonitoredProducts(platform);
      }
      alert(result.message);
      setShowDeleteModal(null);
      setSelectedProduct(null);
      setSellers([]);
      void Promise.all([loadProducts(), loadLastInactive()]);
    } catch (e) {
      console.error('Error deleting products:', e);
      alert('Delete failed');
    } finally {
      setDeleteLoading(false);
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
    "campaignPrice": 284.99,
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
    "campaignPrice": 284.99,
    "sellerStockCode": "STK001"
  }
]`;
  };

  const progressPercent = fetchProgress.total > 0
    ? Math.min(100, Math.round((fetchProgress.completed / fetchProgress.total) * 100))
    : 0;

  return {
    // State
    platform,
    products,
    loading,
    selectedProduct,
    sellers,
    sellersLoading,
    showImportModal,
    importJson,
    importLoading,
    fetchTaskId,
    fetchStatus,
    fetchProgress,
    exportLoading,
    showInactive,
    showExportMenu,
    brands,
    selectedBrand,
    priceAlertOnly,
    campaignAlertOnly,
    searchInput,
    searchQuery,
    lastInactiveCount,
    showFetchMenu,
    currentFetchType,
    showDeleteModal,
    deleteLoading,
    totalProducts,
    activeTotalCount,
    inactiveTotalCount,
    currentOffset,

    // Derived
    activeProducts,
    inactiveProducts,
    progressPercent,

    // Setters
    setPlatform,
    setShowImportModal,
    setImportJson,
    setShowInactive,
    setShowExportMenu,
    setSelectedBrand,
    setPriceAlertOnly,
    setCampaignAlertOnly,
    setSearchInput,
    setShowFetchMenu,
    setShowDeleteModal,
    setCurrentOffset,

    // Refs
    currentOffsetRef,

    // Handlers
    handleProductClick,
    handleImport,
    handleFetchAll,
    handleStopFetch,
    handleFetchSingle,
    handleDelete,
    handleExport,
    handleBulkDelete,
    loadProducts,

    // Utilities
    formatPrice,
    formatDate,
    getProductUrl,
    getImportExample,
  };
}

export type UsePriceMonitorReturn = ReturnType<typeof usePriceMonitor>;
