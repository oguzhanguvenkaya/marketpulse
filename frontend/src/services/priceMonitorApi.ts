import api, { CACHE_PREFIX, buildCacheKey, getCachedOrFetch, invalidatePriceMonitorCache } from './client';
import type {
  MonitoredProductsResponse,
  GetProductsParams,
  RequestOptions,
  ProductWithSellers,
  BulkProductInput,
  FetchType,
  FetchTask,
  LastInactiveProduct,
  ExportActiveFilter,
} from './types';

export const getMonitoredProducts = async (
  platform?: string,
  params?: Partial<GetProductsParams>,
  options: RequestOptions = {},
): Promise<MonitoredProductsResponse> => {
  const queryParams: Record<string, unknown> = { ...params };
  if (platform) queryParams.platform = platform;
  const cacheKey = buildCacheKey(CACHE_PREFIX.priceMonitorProducts, queryParams);
  return getCachedOrFetch(
    cacheKey,
    async () => {
      const response = await api.get('/price-monitor/products', {
        params: queryParams,
        signal: options.signal,
      });
      return response.data;
    },
    {
      forceRefresh: options.forceRefresh,
      skipDedupe: Boolean(options.signal),
    },
  );
};

export const getBrands = async (platform?: string): Promise<{ brands: string[] }> => {
  const params = platform ? { platform } : {};
  const cacheKey = buildCacheKey(CACHE_PREFIX.priceMonitorBrands, params);
  return getCachedOrFetch(cacheKey, async () => {
    const response = await api.get('/price-monitor/brands', { params });
    return response.data;
  });
};

export const getMonitoredProductDetail = async (productId: string): Promise<ProductWithSellers> => {
  const response = await api.get(`/price-monitor/products/${productId}`);
  return response.data;
};

export const addMonitoredProducts = async (products: BulkProductInput[], platform: string = 'hepsiburada'): Promise<{ added: number; updated: number; errors: unknown[]; total: number; platform: string }> => {
  const response = await api.post('/price-monitor/products', { products, platform });
  invalidatePriceMonitorCache();
  return response.data;
};

export const deleteMonitoredProduct = async (productId: string): Promise<void> => {
  await api.delete(`/price-monitor/products/${productId}`);
  invalidatePriceMonitorCache();
};

export const deleteAllMonitoredProducts = async (platform: string): Promise<{ success: boolean; deleted_count: number; message: string }> => {
  const response = await api.delete('/price-monitor/products/bulk/all', { params: { platform } });
  invalidatePriceMonitorCache();
  return response.data;
};

export const deleteInactiveMonitoredProducts = async (platform: string): Promise<{ success: boolean; deleted_count: number; message: string }> => {
  const response = await api.delete('/price-monitor/products/bulk/inactive', { params: { platform } });
  invalidatePriceMonitorCache();
  return response.data;
};

export const startFetchTask = async (platform: string = 'hepsiburada', fetchType: FetchType = 'active'): Promise<{ task_id: string; platform: string; fetch_type: string; status: string; message: string; executor?: string }> => {
  const response = await api.post('/price-monitor/fetch', null, {
    params: { platform, fetch_type: fetchType }
  });
  invalidatePriceMonitorCache();
  return response.data;
};

export const stopFetchTask = async (taskId: string): Promise<{ success: boolean; message: string }> => {
  const response = await api.post(`/price-monitor/fetch/${taskId}/stop`);
  invalidatePriceMonitorCache();
  return response.data;
};

export const getFetchTaskStatus = async (taskId: string): Promise<FetchTask & { fetch_type?: string; last_inactive_count?: number; executor?: string }> => {
  const response = await api.get(`/price-monitor/fetch/${taskId}`);
  return response.data;
};

export const getActiveFetchTask = async (platform: string = 'hepsiburada'): Promise<{
  active: boolean;
  id?: string;
  status?: string;
  total_products?: number;
  completed_products?: number;
  failed_products?: number;
  fetch_type?: string;
}> => {
  const response = await api.get('/price-monitor/fetch/active', { params: { platform } });
  return response.data;
};

export const getLastInactiveSkus = async (platform: string = 'hepsiburada'): Promise<{
  skus: string[];
  count: number;
  products: LastInactiveProduct[];
  task_id: string | null;
  completed_at: string | null;
}> => {
  const params = { platform };
  const cacheKey = buildCacheKey(CACHE_PREFIX.priceMonitorLastInactive, params);
  return getCachedOrFetch(cacheKey, async () => {
    const response = await api.get('/price-monitor/last-inactive', {
      params,
    });
    return response.data;
  });
};

export const fetchSingleProduct = async (productId: string): Promise<{ success: boolean; message: string }> => {
  const response = await api.post(`/price-monitor/fetch-single/${productId}`);
  invalidatePriceMonitorCache();
  return response.data;
};

export const exportPriceMonitorData = async (
  platform: string,
  activeFilter: ExportActiveFilter = 'all'
): Promise<void> => {
  const response = await api.get('/price-monitor/export', {
    params: { platform, active_filter: activeFilter },
    responseType: 'blob'
  });

  const blob = new Blob([response.data], {
    type: 'application/json'
  });

  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;

  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
  link.download = `price_monitor_${platform}_${timestamp}.json`;

  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
};

export const exportPriceMonitorExcel = async (
  platform: string | null = null,
  activeFilter: ExportActiveFilter = 'all'
): Promise<void> => {
  const params: Record<string, string> = { active_filter: activeFilter };
  if (platform) params.platform = platform;

  const response = await api.get('/price-monitor/export-excel', {
    params,
    responseType: 'blob',
  });

  const blob = new Blob([response.data], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  });

  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;

  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
  const suffix = platform || 'all';
  link.download = `price_monitor_categories_${suffix}_${timestamp}.xlsx`;

  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
};
