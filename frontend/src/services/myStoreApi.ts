import api, { CACHE_PREFIX, buildCacheKey, getCachedOrFetch, invalidateMyStoreCache } from './client';
import type { MyStoreListResponse, MyStoreProductDetail, MyStorePlatformFilter, RequestOptions } from './types';

export interface MyStoreGetParams {
  platform_filter?: MyStorePlatformFilter;
  search?: string;
  brand?: string;
  limit?: number;
  offset?: number;
}

export const getMyStoreProducts = async (
  params?: MyStoreGetParams,
  options: RequestOptions = {},
): Promise<MyStoreListResponse> => {
  const cacheKey = buildCacheKey(CACHE_PREFIX.myStoreProducts, params || {});
  return getCachedOrFetch(
    cacheKey,
    async () => {
      const response = await api.get('/my-store/products', {
        params,
        signal: options.signal,
      });
      return response.data;
    },
    { forceRefresh: options.forceRefresh, skipDedupe: Boolean(options.signal) },
  );
};

export const getMyStoreProductDetail = async (productId: number): Promise<MyStoreProductDetail> => {
  const response = await api.get(`/my-store/products/${productId}`);
  return response.data;
};

export interface CsvPreviewResponse {
  headers: string[];
  preview_rows: Record<string, string>[];
  row_count: number;
  delimiter: string;
  suggested_mapping: Record<string, string>;
}

export const previewMyStoreCsv = async (file: File): Promise<CsvPreviewResponse> => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post('/my-store/preview-csv', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

export const importMyStoreCsv = async (
  file: File,
  mapping?: Record<string, string>,
): Promise<{ added: number; updated: number; errors: unknown[]; total: number }> => {
  const formData = new FormData();
  formData.append('file', file);
  if (mapping) {
    formData.append('mapping', JSON.stringify(mapping));
  }
  const response = await api.post('/my-store/import-csv', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  invalidateMyStoreCache();
  return response.data;
};

export const deleteMyStoreProduct = async (productId: number): Promise<void> => {
  await api.delete(`/my-store/products/${productId}`);
  invalidateMyStoreCache();
};

export const deleteAllMyStoreProducts = async (): Promise<{ deleted: number }> => {
  const response = await api.delete('/my-store/products/bulk/all');
  invalidateMyStoreCache();
  return response.data;
};

export const getMyStoreBrands = async (): Promise<{ brands: string[] }> => {
  const cacheKey = buildCacheKey(CACHE_PREFIX.myStoreBrands, {});
  return getCachedOrFetch(cacheKey, async () => {
    const response = await api.get('/my-store/brands');
    return response.data;
  });
};

export const getMyStoreStats = async (): Promise<{ total: number; hb_matched: number; ty_matched: number }> => {
  const response = await api.get('/my-store/stats');
  return response.data;
};
