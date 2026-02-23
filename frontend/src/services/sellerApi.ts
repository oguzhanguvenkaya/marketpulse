import api, { CACHE_PREFIX, buildCacheKey, getCachedOrFetch } from './client';
import type { SellersResponse, SellerProductsResponse } from './types';

export const getSellers = async (
  platform: string,
  options: { limit?: number; offset?: number } = {},
): Promise<SellersResponse> => {
  const params = { platform, limit: options.limit, offset: options.offset };
  const cacheKey = buildCacheKey(CACHE_PREFIX.sellers, params);
  return getCachedOrFetch(cacheKey, async () => {
    const response = await api.get('/sellers', { params });
    return response.data;
  });
};

export const getSellerProducts = async (
  merchantId: string,
  platform: string,
  priceAlertOnly: boolean = false,
  campaignAlertOnly: boolean = false,
  options: { limit?: number; offset?: number } = {},
): Promise<SellerProductsResponse> => {
  const params = {
    platform,
    price_alert_only: priceAlertOnly,
    campaign_alert_only: campaignAlertOnly,
    limit: options.limit,
    offset: options.offset,
  };
  const cacheKey = buildCacheKey(CACHE_PREFIX.sellerProducts, { merchantId, ...params });
  return getCachedOrFetch(cacheKey, async () => {
    const response = await api.get(`/sellers/${merchantId}/products`, {
      params,
    });
    return response.data;
  });
};

export const exportSellerProducts = async (
  merchantId: string,
  platform: string,
  priceAlertOnly: boolean = false,
  campaignAlertOnly: boolean = false
): Promise<void> => {
  const response = await api.get(
    `/sellers/${merchantId}/export`,
    {
      params: {
        platform,
        price_alert_only: priceAlertOnly,
        campaign_alert_only: campaignAlertOnly,
      },
      responseType: 'blob',
    }
  );

  const contentDisposition = response.headers['content-disposition'];
  let filename = 'seller_products.csv';
  if (contentDisposition) {
    const match = contentDisposition.match(/filename=(.+)/);
    if (match) filename = match[1];
  }

  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
};
