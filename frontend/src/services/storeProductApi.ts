import api from './client';
import type { StoreProductListResponse, StoreProductFilters, CategoryTreeNode, StoreProduct, ScrapeJobStatus } from './types';

export const getStoreProducts = async (params: {
  platform?: string;
  brand?: string;
  category?: string;
  search?: string;
  min_price?: number;
  max_price?: number;
  min_rating?: number;
  sku?: string;
  barcode?: string;
  sort_by?: string;
  sort_dir?: string;
  page?: number;
  page_size?: number;
}): Promise<StoreProductListResponse> => {
  const response = await api.get('/store-products', { params });
  return response.data;
};

export const getStoreProductFilters = async (platform?: string): Promise<StoreProductFilters> => {
  const response = await api.get('/store-products/filters', { params: { platform } });
  return response.data;
};

export const getStoreCategoryTree = async (platform?: string): Promise<{ tree: CategoryTreeNode[] }> => {
  const response = await api.get('/store-products/category-tree', { params: { platform } });
  return response.data;
};

export const getStoreProductStats = async (): Promise<{ total_products: number; by_platform: Record<string, number> }> => {
  const response = await api.get('/store-products/stats');
  return response.data;
};

export const getStoreProduct = async (productId: string): Promise<StoreProduct> => {
  const response = await api.get(`/store-products/${productId}`);
  return response.data;
};

export const scrapeFromPriceMonitor = async (platform?: string): Promise<{ job_id: string; status: string; total_urls: number }> => {
  const response = await api.post('/store-products/scrape-from-monitor', null, { params: { platform } });
  return response.data;
};

export const getScrapeJobStatus = async (jobId: string): Promise<ScrapeJobStatus> => {
  const response = await api.get(`/store-products/scrape-job-status/${jobId}`);
  return response.data;
};

export const saveFromScrapeJob = async (jobId: string): Promise<{ saved: number; updated: number; total_results: number }> => {
  const response = await api.post(`/store-products/save-from-scrape-job/${jobId}`);
  return response.data;
};

export const deleteStoreProduct = async (productId: string): Promise<void> => {
  await api.delete(`/store-products/${productId}`);
};

export const deleteAllStoreProducts = async (platform?: string): Promise<{ deleted: number }> => {
  const response = await api.delete('/store-products', { params: { platform } });
  return response.data;
};

export const scrapeFromUrls = async (urls: string[]): Promise<{ job_id: string; status: string; total_urls: number }> => {
  const response = await api.post('/store-products/scrape-from-urls', { urls });
  return response.data;
};

export const backfillPrices = async (platform?: string): Promise<{ message: string; updated: number; total_without_price: number }> => {
  const response = await api.post('/store-products/backfill-prices', null, { params: { platform } });
  return response.data;
};

export const importExcelProducts = async (file: File): Promise<{ created: number; updated: number; skipped: number; total_rows: number; filename: string }> => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post('/store-products/import-excel', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  });
  return response.data;
};
