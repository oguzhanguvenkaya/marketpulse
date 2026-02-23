import api from './client';
import type { CategoryProductListResponse, CategoryFilterData } from './types';

export const scrapeCategoryPage = async (url: string, page: number = 1, sessionId?: string, pageCount: number = 1) => {
  const response = await api.post('/category-explorer/scrape-page', {
    url,
    page,
    session_id: sessionId || null,
    page_count: pageCount,
  }, { timeout: 300000 });
  return response.data;
};

export const getCategorySessions = async (platform?: string) => {
  const params: Record<string, string> = {};
  if (platform) params.platform = platform;
  const response = await api.get('/category-explorer/sessions', { params });
  return response.data;
};

export const getCategorySession = async (sessionId: string) => {
  const response = await api.get(`/category-explorer/sessions/${sessionId}`);
  return response.data;
};

export const deleteCategorySession = async (sessionId: string) => {
  const response = await api.delete(`/category-explorer/sessions/${sessionId}`);
  return response.data;
};

export const fetchCategoryProductDetail = async (productIds: number[]) => {
  const response = await api.post('/category-explorer/fetch-detail', {
    product_ids: productIds,
  });
  return response.data;
};

export const bulkFetchCategoryDetails = async (sessionId: string, productIds?: number[]) => {
  const response = await api.post('/category-explorer/bulk-fetch', {
    session_id: sessionId,
    product_ids: productIds || null,
  });
  return response.data;
};

export const getCategoryFetchStatus = async (sessionId: string) => {
  const response = await api.get(`/category-explorer/fetch-status/${sessionId}`);
  return response.data;
};

export const getCategoryProductDetail = async (productId: number) => {
  const response = await api.get(`/category-explorer/products/${productId}`);
  return response.data;
};

export const getCategoryProductsByCategory = async (params: {
  category?: string;
  platform?: string;
  search?: string;
  session_id?: string;
  brand?: string;
  seller?: string;
  min_price?: number;
  max_price?: number;
  min_rating?: number;
  is_sponsored?: boolean;
  sort_by?: string;
  sort_dir?: string;
  page?: number;
  page_size?: number;
}): Promise<CategoryProductListResponse> => {
  const response = await api.get('/category-explorer/products-by-category', { params });
  return response.data;
};

export const getCategoryPageFilters = async (params: {
  session_id?: string;
  category?: string;
  platform?: string;
}): Promise<CategoryFilterData> => {
  const response = await api.get('/category-explorer/category-filters', { params });
  return response.data;
};

export const deleteCategoryProduct = async (productId: number) => {
  const response = await api.delete(`/category-explorer/products/${productId}`);
  return response.data;
};

export const deleteCategoryProductsBulk = async (productIds: number[]) => {
  const response = await api.post('/category-explorer/delete-products', {
    product_ids: productIds,
  });
  return response.data;
};

export const lookupSessionUrl = async (category: string, platform?: string): Promise<{category_url: string | null; session_id?: string; category_name?: string}> => {
  const params: Record<string, string> = { category };
  if (platform) params.platform = platform;
  const response = await api.get('/category-explorer/session-url-lookup', { params });
  return response.data;
};
