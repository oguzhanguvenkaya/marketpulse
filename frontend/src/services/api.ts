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
  url: string;
  name?: string;
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

export default api;
