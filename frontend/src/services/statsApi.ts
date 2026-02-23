import api, { CACHE_PREFIX, buildCacheKey, getCachedOrFetch } from './client';
import type { Stats, StatTrends } from './types';

export const getStats = async (): Promise<Stats> => {
  const cacheKey = buildCacheKey(CACHE_PREFIX.stats);
  return getCachedOrFetch(cacheKey, async () => {
    const response = await api.get('/stats');
    return response.data;
  });
};

export const getStatTrends = async (): Promise<StatTrends | null> => {
  try {
    const response = await api.get('/stats/trends');
    return response.data;
  } catch {
    // Backend endpoint may not exist yet — graceful fallback
    return null;
  }
};
