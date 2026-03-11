import { useState, useEffect, useCallback, useRef } from 'react';
import type { MyStoreProduct, MyStoreProductDetail, MyStorePlatformFilter } from '../services/types';
import {
  getMyStoreProducts,
  getMyStoreProductDetail,
  importMyStoreCsv,
  deleteMyStoreProduct,
  deleteAllMyStoreProducts,
  getMyStoreBrands,
} from '../services/myStoreApi';

const PAGE_SIZE = 100;
const SEARCH_DEBOUNCE_MS = 400;

export function useMyStore() {
  // Platform & filter state
  const [platformFilter, setPlatformFilter] = useState<MyStorePlatformFilter>('all');
  const [searchInput, setSearchInput] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedBrand, setSelectedBrand] = useState('');
  const [brands, setBrands] = useState<string[]>([]);

  // Data state
  const [products, setProducts] = useState<MyStoreProduct[]>([]);
  const [totalProducts, setTotalProducts] = useState(0);
  const [loading, setLoading] = useState(false);
  const [currentOffset, setCurrentOffset] = useState(0);
  const [stats, setStats] = useState<{ web_count: number; hb_matched: number; ty_matched: number }>({
    web_count: 0, hb_matched: 0, ty_matched: 0,
  });

  // Selection & detail state
  const [selectedProduct, setSelectedProduct] = useState<MyStoreProduct | null>(null);
  const [productDetail, setProductDetail] = useState<MyStoreProductDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [selectedPlatformCard, setSelectedPlatformCard] = useState<'web' | 'hepsiburada' | 'trendyol' | null>(null);

  // Modal state
  const [showImportModal, setShowImportModal] = useState(false);
  const [importLoading, setImportLoading] = useState(false);
  const [showDeleteAllModal, setShowDeleteAllModal] = useState(false);

  // Abort controller
  const abortRef = useRef<AbortController | null>(null);

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => setSearchQuery(searchInput), SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [searchInput]);

  // Load brands
  const loadBrands = useCallback(async () => {
    try {
      const data = await getMyStoreBrands();
      setBrands(data.brands);
    } catch {
      /* ignore */
    }
  }, []);

  // Load products
  const loadProducts = useCallback(async (offset = 0) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setLoading(true);
    try {
      const data = await getMyStoreProducts(
        {
          platform_filter: platformFilter,
          search: searchQuery || undefined,
          brand: selectedBrand || undefined,
          limit: PAGE_SIZE,
          offset,
        },
        { signal: controller.signal },
      );
      if (abortRef.current !== controller) return;
      setProducts(data.products);
      setTotalProducts(data.total);
      setStats(data.stats);
      setCurrentOffset(offset);
    } catch (err: unknown) {
      if (err instanceof Error && err.name === 'CanceledError') return;
    } finally {
      setLoading(false);
    }
  }, [platformFilter, searchQuery, selectedBrand]);

  // Effects
  useEffect(() => {
    loadProducts(0);
    loadBrands();
  }, [loadProducts, loadBrands]);

  useEffect(() => {
    setCurrentOffset(0);
  }, [platformFilter, searchQuery, selectedBrand]);

  // Handlers
  const handleProductClick = useCallback(async (product: MyStoreProduct) => {
    setSelectedProduct(product);
    setSelectedPlatformCard(null);
    setDetailLoading(true);
    try {
      const detail = await getMyStoreProductDetail(product.id);
      setProductDetail(detail);
    } catch {
      setProductDetail(null);
    } finally {
      setDetailLoading(false);
    }
  }, []);

  const handlePlatformCardClick = useCallback((platform: 'web' | 'hepsiburada' | 'trendyol') => {
    setSelectedPlatformCard(platform);
  }, []);

  const handleClosePlatformDrawer = useCallback(() => {
    setSelectedPlatformCard(null);
  }, []);

  const handleImportCsv = useCallback(async (file: File, mapping?: Record<string, string>) => {
    setImportLoading(true);
    try {
      const result = await importMyStoreCsv(file, mapping);
      setShowImportModal(false);
      await loadProducts(0);
      await loadBrands();
      return result;
    } finally {
      setImportLoading(false);
    }
  }, [loadProducts, loadBrands]);

  const handleDeleteProduct = useCallback(async (productId: number) => {
    await deleteMyStoreProduct(productId);
    if (selectedProduct?.id === productId) {
      setSelectedProduct(null);
      setProductDetail(null);
    }
    await loadProducts(currentOffset);
  }, [selectedProduct, currentOffset, loadProducts]);

  const handleDeleteAll = useCallback(async () => {
    await deleteAllMyStoreProducts();
    setSelectedProduct(null);
    setProductDetail(null);
    setShowDeleteAllModal(false);
    await loadProducts(0);
    await loadBrands();
  }, [loadProducts, loadBrands]);

  const handlePrevPage = useCallback(() => {
    const newOffset = Math.max(0, currentOffset - PAGE_SIZE);
    loadProducts(newOffset);
  }, [currentOffset, loadProducts]);

  const handleNextPage = useCallback(() => {
    const newOffset = currentOffset + PAGE_SIZE;
    if (newOffset < totalProducts) loadProducts(newOffset);
  }, [currentOffset, totalProducts, loadProducts]);

  const formatPrice = useCallback((price?: number | null) => {
    if (price == null) return '-';
    return new Intl.NumberFormat('tr-TR', { style: 'currency', currency: 'TRY', maximumFractionDigits: 0 }).format(price);
  }, []);

  return {
    // Filter state
    platformFilter, setPlatformFilter,
    searchInput, setSearchInput,
    selectedBrand, setSelectedBrand,
    brands,
    // Data
    products, totalProducts, loading, stats,
    currentOffset, PAGE_SIZE,
    // Selection & detail
    selectedProduct, setSelectedProduct,
    productDetail, detailLoading,
    selectedPlatformCard,
    handleProductClick, handlePlatformCardClick, handleClosePlatformDrawer,
    // Modals & actions
    showImportModal, setShowImportModal,
    importLoading, handleImportCsv,
    showDeleteAllModal, setShowDeleteAllModal, handleDeleteAll,
    handleDeleteProduct,
    // Pagination
    handlePrevPage, handleNextPage,
    // Utils
    formatPrice,
  };
}

export type UseMyStoreReturn = ReturnType<typeof useMyStore>;
