import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
});

export interface SearchTask {
  id: string;
  keyword: string;
  platform: string;
  status: string;
  total_products: number;
  created_at: string;
}

export interface Coupon {
  amount?: number;
  min_order?: number;
}

export interface Campaign {
  name: string;
  url?: string;
}

export interface Seller {
  seller_name: string;
  seller_rating?: number;
  price?: number;
  is_authorized: boolean;
}

export interface Review {
  author?: string;
  rating?: number;
  review_text?: string;
  review_date?: string;
  seller_name?: string;
}

export interface Product {
  id: string;
  platform: string;
  external_id: string;
  sku?: string;
  barcode?: string;
  name: string;
  url: string;
  brand?: string;
  seller_name?: string;
  seller_rating?: number;
  category_path?: string;
  category_hierarchy?: string;
  image_url?: string;
  description?: string;
  origin_country?: string;
  latest_price?: number;
  discounted_price?: number;
  discount_percentage?: number;
  latest_rating?: number;
  reviews_count?: number;
  stock_count?: number;
  in_stock?: boolean;
  is_sponsored?: boolean;
  coupons?: Coupon[];
  campaigns?: Campaign[];
}

export interface ProductDetail extends Product {
  other_sellers: Seller[];
  reviews: Review[];
}

export interface Snapshot {
  id: number;
  price?: number;
  discounted_price?: number;
  discount_percentage?: number;
  rating?: number;
  reviews_count?: number;
  stock_count?: number;
  in_stock: boolean;
  is_sponsored: boolean;
  coupons?: Coupon[];
  campaigns?: Campaign[];
  snapshot_date: string;
}

export interface Stats {
  total_products: number;
  total_snapshots: number;
  total_tasks: number;
  completed_tasks: number;
  total_sellers?: number;
  total_reviews?: number;
}

export const createSearchTask = async (keyword: string, platform: string = 'hepsiburada'): Promise<SearchTask> => {
  const response = await api.post('/search', { keyword, platform });
  return response.data;
};

export const getSearchTask = async (taskId: string): Promise<SearchTask> => {
  const response = await api.get(`/search/${taskId}`);
  return response.data;
};

export const getTasks = async (limit: number = 10): Promise<SearchTask[]> => {
  const response = await api.get('/tasks', { params: { limit } });
  return response.data;
};

export const getProducts = async (keyword?: string, platform?: string, limit: number = 50): Promise<Product[]> => {
  const response = await api.get('/products', { params: { keyword, platform, limit } });
  return response.data;
};

export const getProduct = async (productId: string): Promise<ProductDetail> => {
  const response = await api.get(`/products/${productId}`);
  return response.data;
};

export const getProductSnapshots = async (productId: string, days: number = 30): Promise<Snapshot[]> => {
  const response = await api.get(`/products/${productId}/snapshots`, { params: { days } });
  return response.data;
};

export const analyzeProducts = async (productIds: string[], question?: string): Promise<{ analysis: string }> => {
  const response = await api.post('/analyze', { product_ids: productIds, question });
  return response.data;
};

export const getStats = async (): Promise<Stats> => {
  const response = await api.get('/stats');
  return response.data;
};

export interface SponsoredProduct {
  order_index: number;
  product_url: string;
  product_name?: string;
  seller_name?: string;
  price?: number;
  discounted_price?: number;
  image_url?: string;
  snapshot_date?: string;
}

export interface BrandProduct {
  url?: string;
  name?: string;
  price?: number;
  discounted_price?: number;
  image_url?: string;
}

export interface SponsoredBrand {
  seller_name: string;
  seller_id?: string;
  position?: number;
  products?: BrandProduct[];
  snapshot_date?: string;
}

export interface SponsoredProductsResponse {
  keyword: string;
  total_sponsored: number;
  sponsored_products: SponsoredProduct[];
}

export interface SponsoredBrandsResponse {
  keyword: string;
  sponsored_brands: SponsoredBrand[];
}

export const getSponsoredProducts = async (taskId: string): Promise<SponsoredProductsResponse> => {
  const response = await api.get(`/search/${taskId}/sponsored-products`);
  return response.data;
};

export const getSponsoredBrands = async (taskId: string): Promise<SponsoredBrandsResponse> => {
  const response = await api.get(`/search/${taskId}/sponsored-brands`);
  return response.data;
};

export interface MonitoredProduct {
  id: string;
  platform: string;
  sku: string;
  barcode?: string;
  product_url: string;
  product_name?: string;
  brand?: string;
  seller_stock_code?: string;
  threshold_price?: number;
  alert_campaign_price?: number;
  image_url?: string;
  is_active: boolean;
  last_fetched_at?: string;
  seller_count: number;
  has_price_alert: boolean;
  price_alert_count: number;
  has_campaign_alert: boolean;
  campaign_alert_count: number;
}

export interface SellerSnapshot {
  merchant_id: string;
  merchant_name: string;
  merchant_logo?: string;
  merchant_url_postfix?: string;
  merchant_url?: string;
  merchant_rating?: number;
  merchant_rating_count?: number;
  merchant_city?: string;
  price: number;
  list_price?: number;
  original_price?: number;
  minimum_price?: number;
  discount_rate?: number;
  stock_quantity?: number;
  buybox_order?: number;
  free_shipping: boolean;
  fast_shipping: boolean;
  is_fulfilled_by_hb: boolean;
  campaigns?: string[];
  campaign_price?: number;
  snapshot_date: string;
  price_alert: boolean;
  campaign_alert?: boolean;
}

export interface MonitoredProductsResponse {
  products: MonitoredProduct[];
  total: number;
}

export interface ProductWithSellers {
  product: MonitoredProduct;
  sellers: SellerSnapshot[];
}

export interface FetchTask {
  id: string;
  status: string;
  total_products: number;
  completed_products: number;
  failed_products: number;
  created_at: string;
  completed_at?: string;
}

export interface BulkProductInput {
  productUrl?: string;
  productName?: string;
  sku?: string;
  barcode?: string;
  brand?: string;
  price?: number;
  campaignPrice?: number;
  sellerStockCode?: string;
}

export interface GetProductsParams {
  platform?: string;
  brand?: string;
  price_alert_only?: boolean;
  campaign_alert_only?: boolean;
  search?: string;
}

export const getMonitoredProducts = async (platform?: string, params?: Partial<GetProductsParams>): Promise<MonitoredProductsResponse> => {
  const queryParams: Record<string, any> = { ...params };
  if (platform) queryParams.platform = platform;
  const response = await api.get('/price-monitor/products', { params: queryParams });
  return response.data;
};

export const getBrands = async (platform?: string): Promise<{ brands: string[] }> => {
  const params = platform ? { platform } : {};
  const response = await api.get('/price-monitor/brands', { params });
  return response.data;
};

export const getMonitoredProductDetail = async (productId: string): Promise<ProductWithSellers> => {
  const response = await api.get(`/price-monitor/products/${productId}`);
  return response.data;
};

export const addMonitoredProducts = async (products: BulkProductInput[], platform: string = 'hepsiburada'): Promise<{ added: number; updated: number; errors: any[]; total: number; platform: string }> => {
  const response = await api.post('/price-monitor/products', { products, platform });
  return response.data;
};

export const deleteMonitoredProduct = async (productId: string): Promise<void> => {
  await api.delete(`/price-monitor/products/${productId}`);
};

export const deleteAllMonitoredProducts = async (platform: string): Promise<{ success: boolean; deleted_count: number; message: string }> => {
  const response = await api.delete('/price-monitor/products/bulk/all', { params: { platform } });
  return response.data;
};

export const deleteInactiveMonitoredProducts = async (platform: string): Promise<{ success: boolean; deleted_count: number; message: string }> => {
  const response = await api.delete('/price-monitor/products/bulk/inactive', { params: { platform } });
  return response.data;
};

export type FetchType = 'active' | 'last_inactive' | 'inactive';

export const startFetchTask = async (platform: string = 'hepsiburada', fetchType: FetchType = 'active'): Promise<{ task_id: string; platform: string; fetch_type: string; status: string; message: string }> => {
  const response = await api.post('/price-monitor/fetch', null, {
    params: { platform, fetch_type: fetchType }
  });
  return response.data;
};

export const stopFetchTask = async (taskId: string): Promise<{ success: boolean; message: string }> => {
  const response = await api.post(`/price-monitor/fetch/${taskId}/stop`);
  return response.data;
};

export const getFetchTaskStatus = async (taskId: string): Promise<FetchTask & { fetch_type?: string; last_inactive_count?: number }> => {
  const response = await api.get(`/price-monitor/fetch/${taskId}`);
  return response.data;
};

export interface LastInactiveProduct {
  id: string;
  sku: string;
  product_name: string;
  brand: string;
  is_active: boolean;
}

export const getLastInactiveSkus = async (platform: string = 'hepsiburada'): Promise<{
  skus: string[];
  count: number;
  products: LastInactiveProduct[];
  task_id: string | null;
  completed_at: string | null;
}> => {
  const response = await api.get('/price-monitor/last-inactive', {
    params: { platform }
  });
  return response.data;
};

export const fetchSingleProduct = async (productId: string): Promise<{ success: boolean; message: string }> => {
  const response = await api.post(`/price-monitor/fetch-single/${productId}`);
  return response.data;
};

export type ExportActiveFilter = 'all' | 'active' | 'inactive';

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

export interface SellerInfo {
  merchant_id: string;
  merchant_name: string;
  merchant_logo?: string;
  merchant_url_postfix?: string;
  merchant_rating?: number;
  product_count: number;
  price_alert_count: number;
  campaign_alert_count: number;
}

export interface SellerProduct {
  product_id: string;
  sku?: string;
  barcode?: string;
  product_name?: string;
  product_url?: string;
  seller_url?: string;
  brand?: string;
  seller_stock_code?: string;
  image_url?: string;
  threshold_price?: number;
  seller_price?: number;
  original_price?: number;
  campaign_price?: number;
  alert_campaign_price?: number;
  campaigns?: string[];
  price_alert: boolean;
  campaign_alert: boolean;
  price_difference?: number;
  campaign_difference?: number;
  snapshot_date: string;
}

export const getSellers = async (platform: string): Promise<{ sellers: SellerInfo[]; total: number }> => {
  const response = await api.get(`/sellers?platform=${platform}`);
  return response.data;
};

export const getSellerProducts = async (
  merchantId: string,
  platform: string,
  priceAlertOnly: boolean = false,
  campaignAlertOnly: boolean = false
): Promise<{ products: SellerProduct[]; total: number; merchant_name: string; price_alert_count: number; campaign_alert_count: number }> => {
  const response = await api.get(`/sellers/${merchantId}/products?platform=${platform}&price_alert_only=${priceAlertOnly}&campaign_alert_only=${campaignAlertOnly}`);
  return response.data;
};

export const exportSellerProducts = async (
  merchantId: string,
  platform: string,
  priceAlertOnly: boolean = false,
  campaignAlertOnly: boolean = false
): Promise<void> => {
  const response = await api.get(
    `/sellers/${merchantId}/export?platform=${platform}&price_alert_only=${priceAlertOnly}&campaign_alert_only=${campaignAlertOnly}`,
    { responseType: 'blob' }
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

export interface ScrapeJobInfo {
  id: string;
  status: string;
  total_urls: number;
  completed_urls: number;
  failed_urls: number;
  created_at: string;
  completed_at?: string;
  error_message?: string;
}

export interface ScrapeResultItem {
  id: number;
  url: string;
  product_name?: string;
  barcode?: string;
  status: string;
  scraped_data?: Record<string, any>;
  error_message?: string;
}

export interface ScrapeJobDetail extends ScrapeJobInfo {
  results: ScrapeResultItem[];
}

export const scrapeUrl = async (url: string, productName?: string, barcode?: string): Promise<{ job_id: string; status: string; total_urls: number }> => {
  const response = await api.post('/url-scraper/scrape', { url, product_name: productName, barcode });
  return response.data;
};

export const scrapeBulkUrls = async (urls: { url: string; product_name?: string; barcode?: string }[]): Promise<{ job_id: string; status: string; total_urls: number }> => {
  const response = await api.post('/url-scraper/scrape-bulk', { urls });
  return response.data;
};

export const scrapeCsv = async (file: File): Promise<{ job_id: string; status: string; total_urls: number }> => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post('/url-scraper/scrape-csv', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return response.data;
};

export const getScrapeJobs = async (limit?: number): Promise<ScrapeJobInfo[]> => {
  const response = await api.get('/url-scraper/jobs', { params: { limit: limit || 20 } });
  return response.data;
};

export const getScrapeJob = async (jobId: string): Promise<ScrapeJobDetail> => {
  const response = await api.get(`/url-scraper/jobs/${jobId}`);
  return response.data;
};

export const downloadScrapeResults = async (jobId: string): Promise<void> => {
  const response = await api.get(`/url-scraper/jobs/${jobId}/download`, { responseType: 'blob' });
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement('a');
  link.href = url;
  link.download = `scrape_results_${jobId.slice(0, 8)}.json`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
};

export const deleteScrapeJob = async (jobId: string): Promise<void> => {
  await api.delete(`/url-scraper/jobs/${jobId}`);
};

export default api;
