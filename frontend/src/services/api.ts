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

export interface Product {
  id: string;
  platform: string;
  external_id: string;
  name: string;
  url: string;
  seller_name?: string;
  category_path?: string;
  image_url?: string;
  latest_price?: number;
  latest_rating?: number;
  reviews_count?: number;
  is_sponsored?: boolean;
}

export interface Snapshot {
  id: number;
  price?: number;
  rating?: number;
  reviews_count?: number;
  in_stock: boolean;
  is_sponsored: boolean;
  snapshot_date: string;
}

export interface Stats {
  total_products: number;
  total_snapshots: number;
  total_tasks: number;
  completed_tasks: number;
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

export const getProduct = async (productId: string): Promise<Product> => {
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

export default api;
