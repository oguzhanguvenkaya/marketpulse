import axios from 'axios';
import { supabase } from '../lib/supabase';
import { invalidateCacheByPrefix } from './queryCache';

const api = axios.create({
  baseURL: '/api',
});

// Request interceptor: Supabase Bearer token ekle
api.interceptors.request.use(async (config) => {
  const { data: { session } } = await supabase.auth.getSession();
  if (session?.access_token) {
    config.headers['Authorization'] = `Bearer ${session.access_token}`;
  }
  return config;
});

// Response interceptor: 401'de login'e redirect
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      supabase.auth.signOut();
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

const CACHE_PREFIX = {
  tasks: 'tasks',
  stats: 'stats',
  priceMonitorProducts: 'price-monitor/products',
  priceMonitorBrands: 'price-monitor/brands',
  priceMonitorLastInactive: 'price-monitor/last-inactive',
  sellers: 'sellers',
  sellerProducts: 'seller-products',
  myStoreProducts: 'my-store/products',
  myStoreBrands: 'my-store/brands',
} as const;

const invalidateDashboardCache = () => {
  invalidateCacheByPrefix(CACHE_PREFIX.tasks);
  invalidateCacheByPrefix(CACHE_PREFIX.stats);
};

const invalidatePriceMonitorCache = () => {
  invalidateCacheByPrefix(CACHE_PREFIX.priceMonitorProducts);
  invalidateCacheByPrefix(CACHE_PREFIX.priceMonitorBrands);
  invalidateCacheByPrefix(CACHE_PREFIX.priceMonitorLastInactive);
  invalidateCacheByPrefix(CACHE_PREFIX.sellers);
  invalidateCacheByPrefix(CACHE_PREFIX.sellerProducts);
};

const invalidateMyStoreCache = () => {
  invalidateCacheByPrefix(CACHE_PREFIX.myStoreProducts);
  invalidateCacheByPrefix(CACHE_PREFIX.myStoreBrands);
};

export { api, CACHE_PREFIX, invalidateDashboardCache, invalidatePriceMonitorCache, invalidateMyStoreCache };
export { buildCacheKey, getCachedOrFetch, invalidateCacheByPrefix } from './queryCache';
export default api;
