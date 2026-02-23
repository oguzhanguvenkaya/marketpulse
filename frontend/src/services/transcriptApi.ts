import api from './client';
import type { TranscriptJobInfo, TranscriptJobDetail } from './types';

export const fetchTranscript = async (videoUrl: string, productName?: string, barcode?: string): Promise<{ job_id: string; status: string; total_videos: number }> => {
  const response = await api.post('/transcripts/fetch', { video_url: videoUrl, product_name: productName, barcode });
  return response.data;
};

export const fetchBulkTranscripts = async (videos: { video_url: string; product_name?: string; barcode?: string }[]): Promise<{ job_id: string; status: string; total_videos: number }> => {
  const response = await api.post('/transcripts/fetch-bulk', { videos });
  return response.data;
};

export const fetchTranscriptCsv = async (file: File): Promise<{ job_id: string; status: string; total_videos: number; skipped_rows?: number; duplicates_removed?: number }> => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post('/transcripts/fetch-csv', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return response.data;
};

export const getTranscriptJobs = async (limit?: number): Promise<TranscriptJobInfo[]> => {
  const response = await api.get('/transcripts/jobs', { params: { limit: limit || 20 } });
  return response.data;
};

export const getTranscriptJob = async (jobId: string): Promise<TranscriptJobDetail> => {
  const response = await api.get(`/transcripts/jobs/${jobId}`);
  return response.data;
};

export const downloadTranscriptResults = async (jobId: string): Promise<void> => {
  const response = await api.get(`/transcripts/jobs/${jobId}/download`, { responseType: 'blob' });
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement('a');
  link.href = url;
  link.download = `transcripts_${jobId.slice(0, 8)}.json`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
};

export const deleteTranscriptJob = async (jobId: string): Promise<void> => {
  await api.delete(`/transcripts/jobs/${jobId}`);
};

export const stopTranscriptJob = async (jobId: string): Promise<{ success: boolean; message: string }> => {
  const response = await api.post(`/transcripts/jobs/${jobId}/stop`);
  return response.data;
};
