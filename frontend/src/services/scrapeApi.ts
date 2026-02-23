import api from './client';
import type { ScrapeJobInfo, ScrapeJobDetail } from './types';

export const scrapeUrl = async (url: string, productName?: string, barcode?: string): Promise<{ job_id: string; status: string; total_urls: number }> => {
  const response = await api.post('/url-scraper/scrape', { url, product_name: productName, barcode });
  return response.data;
};

export const scrapeBulkUrls = async (urls: { url: string; product_name?: string; barcode?: string }[]): Promise<{ job_id: string; status: string; total_urls: number }> => {
  const response = await api.post('/url-scraper/scrape-bulk', { urls });
  return response.data;
};

export const scrapeCsv = async (file: File): Promise<{ job_id: string; status: string; total_urls: number; skipped_rows?: number }> => {
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

export const stopScrapeJob = async (jobId: string): Promise<{ success: boolean; message: string }> => {
  const response = await api.post(`/url-scraper/jobs/${jobId}/stop`);
  return response.data;
};
