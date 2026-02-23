import api from './client';
import type { Product, ProductDetail, Snapshot } from './types';

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
