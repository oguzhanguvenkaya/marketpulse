import { useState, useEffect, useRef, useCallback } from 'react';
import {
  scrapeUrl,
  scrapeBulkUrls,
  scrapeCsv,
  getScrapeJobs,
  getScrapeJob,
  downloadScrapeResults,
  deleteScrapeJob,
} from '../services/api';
import type { ScrapeJobInfo, ScrapeJobDetail, ScrapeResultItem } from '../services/api';

type InputMode = 'single' | 'bulk';
type BulkMode = 'csv' | 'json';

export default function UrlScraper() {
  const [inputMode, setInputMode] = useState<InputMode>('single');
  const [bulkMode, setBulkMode] = useState<BulkMode>('csv');
  const [url, setUrl] = useState('');
  const [productName, setProductName] = useState('');
  const [barcode, setBarcode] = useState('');
  const [jsonInput, setJsonInput] = useState('');
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [scraping, setScraping] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [jobs, setJobs] = useState<ScrapeJobInfo[]>([]);
  const [jobsLoading, setJobsLoading] = useState(true);
  const [expandedJobId, setExpandedJobId] = useState<string | null>(null);
  const [jobDetail, setJobDetail] = useState<ScrapeJobDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadJobs = useCallback(async () => {
    try {
      const data = await getScrapeJobs(20);
      setJobs(data);
    } catch (e) {
      console.error('Error loading jobs:', e);
    } finally {
      setJobsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadJobs();
  }, [loadJobs]);

  useEffect(() => {
    const hasRunning = jobs.some(j => j.status === 'running' || j.status === 'pending');
    if (hasRunning) {
      if (!pollRef.current) {
        pollRef.current = setInterval(loadJobs, 3000);
      }
    } else {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    }
    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [jobs, loadJobs]);

  const handleSingleScrape = async () => {
    if (!url.trim()) {
      setError('Please enter a URL');
      return;
    }
    setError(null);
    setSuccess(null);
    setScraping(true);
    try {
      const result = await scrapeUrl(url.trim(), productName.trim() || undefined, barcode.trim() || undefined);
      setSuccess(`Scrape job started! Job ID: ${result.job_id.slice(0, 8)}... (${result.total_urls} URL)`);
      setUrl('');
      setProductName('');
      setBarcode('');
      loadJobs();
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message || 'Failed to start scraping');
    } finally {
      setScraping(false);
    }
  };

  const handleBulkScrape = async () => {
    setError(null);
    setSuccess(null);
    setScraping(true);
    try {
      if (bulkMode === 'csv') {
        if (!csvFile) {
          setError('Please select a CSV file');
          setScraping(false);
          return;
        }
        const result = await scrapeCsv(csvFile);
        let msg = `Bulk scrape started! Job ID: ${result.job_id.slice(0, 8)}... (${result.total_urls} URLs)`;
        if (result.skipped_rows) msg += ` — ${result.skipped_rows} row(s) skipped (no URLs)`;
        setSuccess(msg);
        setCsvFile(null);
        if (fileInputRef.current) fileInputRef.current.value = '';
      } else {
        if (!jsonInput.trim()) {
          setError('Please enter JSON data');
          setScraping(false);
          return;
        }
        let parsed;
        try {
          parsed = JSON.parse(jsonInput);
        } catch {
          setError('Invalid JSON format');
          setScraping(false);
          return;
        }
        const urls = Array.isArray(parsed) ? parsed : [parsed];
        const result = await scrapeBulkUrls(urls);
        setSuccess(`Bulk scrape started! Job ID: ${result.job_id.slice(0, 8)}... (${result.total_urls} URLs)`);
        setJsonInput('');
      }
      loadJobs();
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message || 'Failed to start bulk scraping');
    } finally {
      setScraping(false);
    }
  };

  const handleViewResults = async (jobId: string) => {
    if (expandedJobId === jobId) {
      setExpandedJobId(null);
      setJobDetail(null);
      return;
    }
    setExpandedJobId(jobId);
    setDetailLoading(true);
    try {
      const detail = await getScrapeJob(jobId);
      setJobDetail(detail);
    } catch (e) {
      console.error('Error loading job detail:', e);
    } finally {
      setDetailLoading(false);
    }
  };

  const handleDownload = async (jobId: string) => {
    try {
      await downloadScrapeResults(jobId);
    } catch (e) {
      console.error('Error downloading results:', e);
    }
  };

  const handleDelete = async (jobId: string) => {
    if (!confirm('Are you sure you want to delete this job?')) return;
    try {
      await deleteScrapeJob(jobId);
      if (expandedJobId === jobId) {
        setExpandedJobId(null);
        setJobDetail(null);
      }
      loadJobs();
    } catch (e) {
      console.error('Error deleting job:', e);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file && (file.name.endsWith('.csv') || file.type === 'text/csv')) {
      setCsvFile(file);
    } else {
      setError('Please drop a valid CSV file');
    }
  };

  const getStatusBadge = (status: string) => {
    const styles: Record<string, string> = {
      pending: 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30',
      running: 'bg-blue-500/20 text-blue-400 border border-blue-500/30',
      completed: 'bg-green-500/20 text-green-400 border border-green-500/30',
      failed: 'bg-red-500/20 text-red-400 border border-red-500/30',
    };
    return (
      <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${styles[status] || 'bg-neutral-500/20 text-neutral-400'}`}>
        {status === 'running' && <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />}
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    );
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const HIDDEN_KEYS = ['source_url', 'json_ld', 'og_data', 'images', 'product_name', 'product_description', 'price', 'currency', 'original_price', 'product_brand', 'product_sku', 'product_barcode', 'product_category', 'page_title', 'h1', 'meta_description', 'product_specs'];
  const FIELD_LABELS: Record<string, string> = {
    product_mpn: 'MPN', product_color: 'Color', product_weight: 'Weight',
    availability: 'Availability', rating: 'Rating', review_count: 'Reviews',
    seller_name: 'Seller', product_image: 'Image URL',
  };

  const renderScrapedData = (item: ScrapeResultItem) => {
    if (!item.scraped_data || Object.keys(item.scraped_data).length === 0) return null;
    const data = item.scraped_data;
    return (
      <div className="mt-3 space-y-3">
        {data.product_name && (
          <div className="text-sm"><span className="text-neutral-400">Name:</span> <span className="text-white font-medium">{data.product_name}</span></div>
        )}
        {(data.product_brand || data.product_sku || data.product_barcode || data.product_category) && (
          <div className="flex flex-wrap gap-3">
            {data.product_brand && <div className="text-sm"><span className="text-neutral-400">Brand:</span> <span className="text-neutral-200">{data.product_brand}</span></div>}
            {data.product_sku && <div className="text-sm"><span className="text-neutral-400">SKU:</span> <span className="text-neutral-200">{data.product_sku}</span></div>}
            {data.product_barcode && <div className="text-sm"><span className="text-neutral-400">Barcode:</span> <span className="text-neutral-200">{data.product_barcode}</span></div>}
            {data.product_category && <div className="text-sm"><span className="text-neutral-400">Category:</span> <span className="text-neutral-200">{data.product_category}</span></div>}
          </div>
        )}
        {data.price !== undefined && (
          <div className="text-sm flex items-center gap-3">
            <span><span className="text-neutral-400">Price:</span> <span className="text-accent-primary font-bold">{data.price} {data.currency || ''}</span></span>
            {data.original_price && <span><span className="text-neutral-400">Was:</span> <span className="text-neutral-500 line-through">{data.original_price}</span></span>}
          </div>
        )}
        {(data.product_description || data.meta_description) && (
          <div className="text-sm">
            <span className="text-neutral-400">Description:</span>
            <div className="text-neutral-300 mt-1 whitespace-pre-line line-clamp-4 bg-dark-800/50 rounded px-3 py-2 border border-dark-600/30">{data.product_description || data.meta_description}</div>
          </div>
        )}
        {data.product_specs && typeof data.product_specs === 'object' && Object.keys(data.product_specs).length > 0 && (
          <div className="text-sm">
            <span className="text-neutral-400">Specifications:</span>
            <div className="mt-1 grid grid-cols-2 gap-x-4 gap-y-1 bg-dark-800/50 rounded px-3 py-2 border border-dark-600/30">
              {Object.entries(data.product_specs).slice(0, 10).map(([k, v]) => (
                <div key={k} className="text-xs">
                  <span className="text-neutral-500">{k}:</span> <span className="text-neutral-300">{String(v)}</span>
                </div>
              ))}
            </div>
          </div>
        )}
        {data.images && Array.isArray(data.images) && data.images.length > 0 && (
          <div className="text-sm"><span className="text-neutral-400">Images:</span> <span className="text-neutral-300">{data.images.length} found</span></div>
        )}
        {Object.entries(data).filter(([key]) => !HIDDEN_KEYS.includes(key)).map(([key, value]) => {
          if (value === null || value === undefined || value === '') return null;
          return (
            <div key={key} className="text-sm">
              <span className="text-neutral-400">{FIELD_LABELS[key] || key}:</span>{' '}
              <span className="text-neutral-300">{typeof value === 'object' ? JSON.stringify(value) : String(value)}</span>
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">URL Scraper</h1>
        <p className="text-neutral-400 mt-1">Scrape product data from URLs - single or bulk</p>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3 text-red-400 text-sm flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-red-400 hover:text-red-300">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
        </div>
      )}

      {success && (
        <div className="bg-green-500/10 border border-green-500/30 rounded-lg px-4 py-3 text-green-400 text-sm flex items-center justify-between">
          <span>{success}</span>
          <button onClick={() => setSuccess(null)} className="text-green-400 hover:text-green-300">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
        </div>
      )}

      <div className="bg-dark-800 border border-white/5 rounded-xl p-6">
        <div className="flex gap-2 mb-6">
          <button
            onClick={() => setInputMode('single')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              inputMode === 'single'
                ? 'bg-accent-primary text-dark-900'
                : 'bg-dark-700 text-neutral-300 hover:bg-dark-600 hover:text-white'
            }`}
          >
            Single URL
          </button>
          <button
            onClick={() => setInputMode('bulk')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              inputMode === 'bulk'
                ? 'bg-accent-primary text-dark-900'
                : 'bg-dark-700 text-neutral-300 hover:bg-dark-600 hover:text-white'
            }`}
          >
            Bulk Import
          </button>
        </div>

        {inputMode === 'single' ? (
          <div className="space-y-4">
            <div>
              <label className="block text-sm text-neutral-400 mb-1.5">URL *</label>
              <input
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://www.example.com/product/..."
                className="w-full bg-dark-700 border border-white/10 text-white rounded-lg px-4 py-2 focus:border-accent-primary focus:outline-none placeholder:text-neutral-500"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-neutral-400 mb-1.5">Product Name (optional)</label>
                <input
                  type="text"
                  value={productName}
                  onChange={(e) => setProductName(e.target.value)}
                  placeholder="Product name"
                  className="w-full bg-dark-700 border border-white/10 text-white rounded-lg px-4 py-2 focus:border-accent-primary focus:outline-none placeholder:text-neutral-500"
                />
              </div>
              <div>
                <label className="block text-sm text-neutral-400 mb-1.5">Barcode (optional)</label>
                <input
                  type="text"
                  value={barcode}
                  onChange={(e) => setBarcode(e.target.value)}
                  placeholder="Barcode / EAN"
                  className="w-full bg-dark-700 border border-white/10 text-white rounded-lg px-4 py-2 focus:border-accent-primary focus:outline-none placeholder:text-neutral-500"
                />
              </div>
            </div>
            <button
              onClick={handleSingleScrape}
              disabled={scraping || !url.trim()}
              className="bg-accent-primary hover:bg-accent-primary/90 text-dark-900 font-medium px-6 py-2 rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {scraping ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-dark-900" />
                  Scraping...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9" />
                  </svg>
                  Scrape
                </>
              )}
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex gap-2 mb-4">
              <button
                onClick={() => setBulkMode('csv')}
                className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                  bulkMode === 'csv'
                    ? 'bg-dark-600 text-white border border-white/10'
                    : 'text-neutral-400 hover:text-white'
                }`}
              >
                CSV Upload
              </button>
              <button
                onClick={() => setBulkMode('json')}
                className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                  bulkMode === 'json'
                    ? 'bg-dark-600 text-white border border-white/10'
                    : 'text-neutral-400 hover:text-white'
                }`}
              >
                JSON Input
              </button>
            </div>

            {bulkMode === 'csv' ? (
              <div>
                <div
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                  className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
                    isDragging
                      ? 'border-accent-primary bg-accent-primary/5'
                      : csvFile
                        ? 'border-green-500/30 bg-green-500/5'
                        : 'border-white/10 hover:border-white/20 bg-dark-700/50'
                  }`}
                >
                  {csvFile ? (
                    <div className="space-y-2">
                      <svg className="w-8 h-8 text-green-400 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <p className="text-white font-medium">{csvFile.name}</p>
                      <p className="text-neutral-400 text-sm">{(csvFile.size / 1024).toFixed(1)} KB</p>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <svg className="w-8 h-8 text-neutral-400 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                      </svg>
                      <p className="text-neutral-300">Drop CSV file here or click to browse</p>
                      <p className="text-neutral-500 text-xs">Supports comma (,) semicolon (;) or tab delimiters. Columns: url (+ url_1, url_2...), product_name (optional), barcode (optional)</p>
                    </div>
                  )}
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".csv"
                    onChange={(e) => setCsvFile(e.target.files?.[0] || null)}
                    className="hidden"
                  />
                </div>
              </div>
            ) : (
              <div>
                <label className="block text-sm text-neutral-400 mb-1.5">JSON Array</label>
                <textarea
                  value={jsonInput}
                  onChange={(e) => setJsonInput(e.target.value)}
                  placeholder={'[\n  { "url": "https://example.com/product1", "product_name": "Product 1", "barcode": "123456" },\n  { "url": "https://example.com/product2" }\n]'}
                  rows={6}
                  className="w-full bg-dark-700 border border-white/10 text-white rounded-lg px-4 py-3 focus:border-accent-primary focus:outline-none placeholder:text-neutral-500 font-mono text-sm"
                />
              </div>
            )}

            <button
              onClick={handleBulkScrape}
              disabled={scraping || (bulkMode === 'csv' ? !csvFile : !jsonInput.trim())}
              className="bg-accent-primary hover:bg-accent-primary/90 text-dark-900 font-medium px-6 py-2 rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {scraping ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-dark-900" />
                  Starting...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                  Start Scraping
                </>
              )}
            </button>
          </div>
        )}
      </div>

      <div className="bg-dark-800 border border-white/5 rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-white">Scrape Jobs</h2>
          <button
            onClick={loadJobs}
            className="bg-dark-700 hover:bg-dark-600 text-neutral-300 px-3 py-1.5 rounded-lg text-sm transition-all flex items-center gap-1.5"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Refresh
          </button>
        </div>

        {jobsLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent-primary" />
          </div>
        ) : jobs.length === 0 ? (
          <div className="text-center py-12">
            <svg className="w-12 h-12 text-neutral-600 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9" />
            </svg>
            <p className="text-neutral-400">No scrape jobs yet</p>
            <p className="text-neutral-500 text-sm mt-1">Start by scraping a URL above</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-xs text-neutral-400 uppercase tracking-wider border-b border-white/5">
                  <th className="pb-3 pr-4">Status</th>
                  <th className="pb-3 pr-4">Total URLs</th>
                  <th className="pb-3 pr-4">Completed</th>
                  <th className="pb-3 pr-4">Failed</th>
                  <th className="pb-3 pr-4">Date</th>
                  <th className="pb-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {jobs.map((job) => (
                  <tr key={job.id} className="group">
                    <td className="py-3 pr-4">{getStatusBadge(job.status)}</td>
                    <td className="py-3 pr-4 text-white text-sm">{job.total_urls}</td>
                    <td className="py-3 pr-4 text-sm">
                      <span className="text-green-400">{job.completed_urls}</span>
                    </td>
                    <td className="py-3 pr-4 text-sm">
                      <span className={job.failed_urls > 0 ? 'text-red-400' : 'text-neutral-500'}>{job.failed_urls}</span>
                    </td>
                    <td className="py-3 pr-4 text-neutral-400 text-sm">{formatDate(job.created_at)}</td>
                    <td className="py-3 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => handleViewResults(job.id)}
                          className={`px-2.5 py-1 rounded-md text-xs font-medium transition-all ${
                            expandedJobId === job.id
                              ? 'bg-accent-primary/20 text-accent-primary border border-accent-primary/30'
                              : 'bg-dark-700 text-neutral-300 hover:bg-dark-600 hover:text-white'
                          }`}
                        >
                          {expandedJobId === job.id ? 'Hide' : 'View'}
                        </button>
                        <button
                          onClick={() => handleDownload(job.id)}
                          className="px-2.5 py-1 rounded-md text-xs font-medium bg-dark-700 text-neutral-300 hover:bg-dark-600 hover:text-white transition-all"
                          title="Download JSON"
                        >
                          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                          </svg>
                        </button>
                        <button
                          onClick={() => handleDelete(job.id)}
                          className="px-2.5 py-1 rounded-md text-xs font-medium bg-dark-700 text-red-400 hover:bg-red-500/20 transition-all"
                          title="Delete job"
                        >
                          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {expandedJobId && (
        <div className="bg-dark-800 border border-white/5 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-lg font-semibold text-white">Job Results</h2>
              <p className="text-neutral-400 text-sm mt-0.5">ID: {expandedJobId.slice(0, 12)}...</p>
            </div>
            <button
              onClick={() => handleDownload(expandedJobId)}
              className="bg-accent-primary hover:bg-accent-primary/90 text-dark-900 font-medium px-4 py-2 rounded-lg transition-all flex items-center gap-2 text-sm"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              Download All as JSON
            </button>
          </div>

          {detailLoading ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-accent-primary" />
            </div>
          ) : jobDetail && jobDetail.results.length > 0 ? (
            <div className="space-y-3">
              {jobDetail.results.map((result) => (
                <div
                  key={result.id}
                  className={`rounded-lg p-4 border ${
                    result.status === 'completed'
                      ? 'bg-dark-700/50 border-white/5'
                      : result.status === 'failed'
                        ? 'bg-red-500/5 border-red-500/20'
                        : 'bg-dark-700/30 border-white/5'
                  }`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        {getStatusBadge(result.status)}
                        {result.product_name && (
                          <span className="text-sm text-white font-medium truncate">{result.product_name}</span>
                        )}
                      </div>
                      <a
                        href={result.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-accent-primary hover:underline truncate block"
                      >
                        {result.url}
                      </a>
                      {result.barcode && (
                        <span className="text-xs text-neutral-500 mt-0.5 block">Barcode: {result.barcode}</span>
                      )}
                      {result.error_message && (
                        <p className="text-xs text-red-400 mt-1">{result.error_message}</p>
                      )}
                      {renderScrapedData(result)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : jobDetail ? (
            <div className="text-center py-8">
              <p className="text-neutral-400">No results yet</p>
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}
