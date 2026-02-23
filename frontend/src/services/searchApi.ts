import api, { CACHE_PREFIX, buildCacheKey, getCachedOrFetch, invalidateDashboardCache } from './client';
import type { SearchTask, SponsoredProductsResponse, SponsoredBrandsResponse } from './types';

export const createSearchTask = async (keyword: string, platform: string = 'hepsiburada'): Promise<SearchTask> => {
  const response = await api.post('/search', { keyword, platform });
  invalidateDashboardCache();
  return response.data;
};

export const getSearchTask = async (taskId: string): Promise<SearchTask> => {
  const response = await api.get(`/search/${taskId}`);
  return response.data;
};

export const getTasks = async (limit: number = 10): Promise<SearchTask[]> => {
  const cacheKey = buildCacheKey(CACHE_PREFIX.tasks, { limit });
  return getCachedOrFetch(cacheKey, async () => {
    const response = await api.get('/tasks', { params: { limit } });
    return response.data;
  });
};

export const getSponsoredProducts = async (taskId: string): Promise<SponsoredProductsResponse> => {
  const response = await api.get(`/search/${taskId}/sponsored-products`);
  return response.data;
};

export const getSponsoredBrands = async (taskId: string): Promise<SponsoredBrandsResponse> => {
  const response = await api.get(`/search/${taskId}/sponsored-brands`);
  return response.data;
};
