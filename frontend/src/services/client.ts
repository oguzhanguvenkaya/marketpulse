import axios from 'axios';
import { invalidateCacheByPrefix } from './queryCache';

const api = axios.create({
  baseURL: '/api',
});

// Request interceptor: attach API key from sessionStorage
api.interceptors.request.use((config) => {
  const apiKey = sessionStorage.getItem('mp_api_key');
  if (apiKey) {
    config.headers['X-API-Key'] = apiKey;
  }
  return config;
});

// Response interceptor: trigger API key prompt on auth failure
let isPromptingApiKey = false;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let pendingAuthQueue: Array<{ resolve: (v: any) => void; reject: (e: any) => void; config: any }> = [];

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if ([401, 403].includes(error.response?.status)) {
      if (isPromptingApiKey) {
        // Queue concurrent 401s to retry after key is entered
        return new Promise((resolve, reject) => {
          pendingAuthQueue.push({ resolve, reject, config: error.config });
        });
      }

      isPromptingApiKey = true;
      window.dispatchEvent(new CustomEvent('mp:api-key-required'));

      return new Promise((resolve, reject) => {
        const handler = (e: Event) => {
          window.removeEventListener('mp:api-key-set', handler);
          isPromptingApiKey = false;
          const key = (e as CustomEvent).detail;
          if (key) {
            error.config.headers['X-API-Key'] = key;
            // Drain queued requests
            const queued = [...pendingAuthQueue];
            pendingAuthQueue = [];
            queued.forEach((q) => {
              q.config.headers['X-API-Key'] = key;
              q.resolve(api.request(q.config));
            });
            resolve(api.request(error.config));
          } else {
            const queued = [...pendingAuthQueue];
            pendingAuthQueue = [];
            queued.forEach((q) => q.reject(error));
            reject(error);
          }
        };
        window.addEventListener('mp:api-key-set', handler);
      });
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

export { api, CACHE_PREFIX, invalidateDashboardCache, invalidatePriceMonitorCache };
export { buildCacheKey, getCachedOrFetch, invalidateCacheByPrefix } from './queryCache';
export default api;
