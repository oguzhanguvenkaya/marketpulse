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
  image_url?: string;
  is_active: boolean;
  last_fetched_at?: string;
  seller_count: number;
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
  original_price?: number;
  minimum_price?: number;
  discount_rate?: number;
  stock_quantity?: number;
  buybox_order?: number;
  free_shipping: boolean;
  fast_shipping: boolean;
  is_fulfilled_by_hb: boolean;
  snapshot_date: string;
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
}

export const getMonitoredProducts = async (platform?: string): Promise<MonitoredProductsResponse> => {
  const params = platform ? { platform } : {};
  const response = await api.get('/price-monitor/products', { params });
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

export const startFetchTask = async (platform: string = 'hepsiburada'): Promise<{ task_id: string; platform: string; status: string; message: string }> => {
  const response = await api.post('/price-monitor/fetch', null, {
    params: { platform }
  });
  return response.data;
};

export const stopFetchTask = async (taskId: string): Promise<{ success: boolean; message: string }> => {
  const response = await api.post(`/price-monitor/fetch/${taskId}/stop`);
  return response.data;
};

export const getFetchTaskStatus = async (taskId: string): Promise<FetchTask> => {
  const response = await api.get(`/price-monitor/fetch/${taskId}`);
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

export default api;
