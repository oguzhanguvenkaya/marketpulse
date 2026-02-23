import { useState, useEffect, useRef, useCallback } from 'react';
import { toast } from 'sonner';
import {
  fetchTranscript,
  fetchBulkTranscripts,
  fetchTranscriptCsv,
  getTranscriptJobs,
  getTranscriptJob,
  downloadTranscriptResults,
  deleteTranscriptJob,
  stopTranscriptJob,
} from '../services/api';
import type { TranscriptJobInfo, TranscriptJobDetail, TranscriptResultItem } from '../services/api';
import ConfirmDialog from '../components/ConfirmDialog';

type InputMode = 'single' | 'bulk';
type BulkMode = 'csv' | 'json';

export default function VideoTranscripts() {
  const [inputMode, setInputMode] = useState<InputMode>('single');
  const [bulkMode, setBulkMode] = useState<BulkMode>('csv');
  const [videoUrl, setVideoUrl] = useState('');
  const [productName, setProductName] = useState('');
  const [barcode, setBarcode] = useState('');
  const [jsonInput, setJsonInput] = useState('');
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [fetching, setFetching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [jobs, setJobs] = useState<TranscriptJobInfo[]>([]);
  const [jobsLoading, setJobsLoading] = useState(true);
  const [expandedJobId, setExpandedJobId] = useState<string | null>(null);
  const [jobDetail, setJobDetail] = useState<TranscriptJobDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [expandedTranscript, setExpandedTranscript] = useState<number | null>(null);
  const [deleteJobId, setDeleteJobId] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const getApiErrorMessage = (error: unknown, fallback: string) => {
    if (error && typeof error === 'object') {
      const withResponse = error as { response?: { data?: { detail?: string } }; message?: string };
      return withResponse.response?.data?.detail || withResponse.message || fallback;
    }
    return fallback;
  };

  const loadJobs = useCallback(async () => {
    try {
      const data = await getTranscriptJobs(20);
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

  const handleSingleFetch = async () => {
    if (!videoUrl.trim()) {
      setError('Please enter a YouTube URL');
      return;
    }
    setError(null);
    setSuccess(null);
    setFetching(true);
    try {
      const result = await fetchTranscript(videoUrl.trim(), productName.trim() || undefined, barcode.trim() || undefined);
      setSuccess(`Transcript job started! Job ID: ${result.job_id.slice(0, 8)}... (${result.total_videos} video)`);
      setVideoUrl('');
      setProductName('');
      setBarcode('');
      loadJobs();
    } catch (e: unknown) {
      setError(getApiErrorMessage(e, 'Failed to start transcript fetch'));
    } finally {
      setFetching(false);
    }
  };

  const handleBulkFetch = async () => {
    setError(null);
    setSuccess(null);
    setFetching(true);
    try {
      if (bulkMode === 'csv') {
        if (!csvFile) {
          setError('Please select a CSV file');
          setFetching(false);
          return;
        }
        const result = await fetchTranscriptCsv(csvFile);
        let msg = `Transcript job started! Job ID: ${result.job_id.slice(0, 8)}... (${result.total_videos} videos)`;
        if (result.skipped_rows) msg += ` — ${result.skipped_rows} row(s) skipped`;
        if (result.duplicates_removed) msg += ` — ${result.duplicates_removed} duplicate(s) removed`;
        setSuccess(msg);
        setCsvFile(null);
        if (fileInputRef.current) fileInputRef.current.value = '';
      } else {
        if (!jsonInput.trim()) {
          setError('Please enter JSON data');
          setFetching(false);
          return;
        }
        let parsed;
        try {
          parsed = JSON.parse(jsonInput);
        } catch {
          setError('Invalid JSON format');
          setFetching(false);
          return;
        }
        const videos = Array.isArray(parsed) ? parsed : [parsed];
        const result = await fetchBulkTranscripts(videos);
        setSuccess(`Transcript job started! Job ID: ${result.job_id.slice(0, 8)}... (${result.total_videos} videos)`);
        setJsonInput('');
      }
      loadJobs();
    } catch (e: unknown) {
      setError(getApiErrorMessage(e, 'Failed to start bulk transcript fetch'));
    } finally {
      setFetching(false);
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
      const detail = await getTranscriptJob(jobId);
      setJobDetail(detail);
    } catch (e) {
      console.error('Error loading job detail:', e);
    } finally {
      setDetailLoading(false);
    }
  };

  const handleDownload = async (jobId: string) => {
    try {
      await downloadTranscriptResults(jobId);
    } catch (e) {
      console.error('Error downloading results:', e);
    }
  };

  const handleDeleteRequest = (jobId: string) => {
    setDeleteJobId(jobId);
  };

  const handleDeleteConfirm = async () => {
    if (!deleteJobId) return;
    const jobId = deleteJobId;
    setDeleteJobId(null);
    try {
      await deleteTranscriptJob(jobId);
      if (expandedJobId === jobId) {
        setExpandedJobId(null);
        setJobDetail(null);
      }
      loadJobs();
      toast.success('Gorev silindi');
    } catch (e) {
      console.error('Error deleting job:', e);
      toast.error('Silme islemi basarisiz');
    }
  };

  const handleStop = async (jobId: string) => {
    try {
      await stopTranscriptJob(jobId);
      loadJobs();
    } catch (e: unknown) {
      console.error('Error stopping job:', e);
      setError(getApiErrorMessage(e, 'Failed to stop job'));
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
      stopped: 'bg-orange-500/20 text-orange-400 border border-orange-500/30',
      skipped: 'bg-neutral-500/20 text-text-muted border border-neutral-500/30',
    };
    return (
      <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${styles[status] || 'bg-neutral-500/20 text-text-muted'}`}>
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

  const renderTranscriptResult = (item: TranscriptResultItem) => {
    const isExpanded = expandedTranscript === item.id;
    return (
      <div key={item.id} className="border border-accent-primary/8 rounded-lg p-3 sm:p-4 bg-dark-800/30">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex flex-wrap items-center gap-2 mb-1">
              {getStatusBadge(item.status)}
              {item.language && (
                <span className="text-xs px-2 py-0.5 rounded bg-accent-secondary/20 text-accent-secondary border border-accent-secondary/30">
                  {item.language} ({item.language_code})
                </span>
              )}
              {item.is_generated && (
                <span className="text-xs px-2 py-0.5 rounded bg-yellow-500/10 text-yellow-500 border border-yellow-500/20">
                  Auto-generated
                </span>
              )}
            </div>
            <a
              href={item.video_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-accent-primary hover:underline break-all"
            >
              {item.video_url}
            </a>
            {item.product_name && (
              <div className="text-xs text-text-muted mt-1">
                Product: <span className="text-text-body">{item.product_name}</span>
                {item.barcode && <> | Barcode: <span className="text-text-body">{item.barcode}</span></>}
              </div>
            )}
            {item.error_message && (
              <div className="text-xs text-red-400 mt-1 bg-red-500/5 border border-red-500/10 rounded px-2 py-1">{item.error_message}</div>
            )}
            {item.status === 'completed' && item.snippet_count !== undefined && (
              <div className="text-xs text-neutral-500 mt-1">{item.snippet_count} transcript segments</div>
            )}
          </div>
          {item.status === 'completed' && item.transcript_text && (
            <button
              onClick={() => setExpandedTranscript(isExpanded ? null : item.id)}
              className="w-full sm:w-auto flex-shrink-0 text-xs px-3 py-1.5 rounded-lg bg-surface-hover hover:bg-surface-hover-active text-text-body transition-all"
            >
              {isExpanded ? 'Hide' : 'Show'} Transcript
            </button>
          )}
        </div>
        {isExpanded && item.transcript_text && (
          <div className="mt-3 bg-dark-800/50 rounded-lg border border-accent-primary/8 p-3 sm:p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-text-muted font-medium">Full Transcript</span>
              <button
                onClick={() => navigator.clipboard.writeText(item.transcript_text || '')}
                className="text-xs text-accent-primary hover:text-accent-primary/80 flex items-center gap-1"
              >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
                Copy
              </button>
            </div>
            <div className="text-sm text-text-body whitespace-pre-line max-h-96 overflow-y-auto leading-relaxed">
              {item.transcript_text}
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="space-y-4 sm:space-y-6">
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold text-text-primary">Video Transcripts</h1>
        <p className="text-sm sm:text-base text-text-muted mt-1">Extract transcripts from YouTube videos - single or bulk</p>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3 text-red-400 text-sm flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <span className="break-words">{error}</span>
          <button onClick={() => setError(null)} className="text-red-400 hover:text-red-300">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
        </div>
      )}

      {success && (
        <div className="bg-green-500/10 border border-green-500/30 rounded-lg px-4 py-3 text-green-400 text-sm flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <span className="break-words">{success}</span>
          <button onClick={() => setSuccess(null)} className="text-green-400 hover:text-green-300">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
        </div>
      )}

      <div className="bg-surface-card border border-accent-primary/8 rounded-xl p-4 sm:p-6">
        <div className="flex gap-2 mb-6 overflow-x-auto pb-1">
          <button
            onClick={() => setInputMode('single')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all whitespace-nowrap ${
              inputMode === 'single'
                ? 'bg-accent-primary text-dark-900 dark:text-accent-on-primary'
                : 'bg-dark-800 text-text-body hover:bg-surface-hover hover:text-text-primary'
            }`}
          >
            Single Video
          </button>
          <button
            onClick={() => setInputMode('bulk')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all whitespace-nowrap ${
              inputMode === 'bulk'
                ? 'bg-accent-primary text-dark-900 dark:text-accent-on-primary'
                : 'bg-dark-800 text-text-body hover:bg-surface-hover hover:text-text-primary'
            }`}
          >
            Bulk Import
          </button>
        </div>

        {inputMode === 'single' ? (
          <div className="space-y-4">
            <div>
              <label className="block text-sm text-text-muted mb-1.5">YouTube URL *</label>
              <input
                type="url"
                value={videoUrl}
                onChange={(e) => setVideoUrl(e.target.value)}
                placeholder="https://www.youtube.com/watch?v=..."
                className="w-full bg-dark-800 border border-accent-primary/12 text-text-primary rounded-lg px-4 py-2 focus:border-accent-primary focus:outline-none placeholder:text-neutral-500"
              />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-text-muted mb-1.5">Product Name (optional)</label>
                <input
                  type="text"
                  value={productName}
                  onChange={(e) => setProductName(e.target.value)}
                  placeholder="Product name"
                  className="w-full bg-dark-800 border border-accent-primary/12 text-text-primary rounded-lg px-4 py-2 focus:border-accent-primary focus:outline-none placeholder:text-neutral-500"
                />
              </div>
              <div>
                <label className="block text-sm text-text-muted mb-1.5">Barcode (optional)</label>
                <input
                  type="text"
                  value={barcode}
                  onChange={(e) => setBarcode(e.target.value)}
                  placeholder="Barcode / EAN"
                  className="w-full bg-dark-800 border border-accent-primary/12 text-text-primary rounded-lg px-4 py-2 focus:border-accent-primary focus:outline-none placeholder:text-neutral-500"
                />
              </div>
            </div>
            <button
              onClick={handleSingleFetch}
              disabled={fetching || !videoUrl.trim()}
              className="w-full sm:w-auto bg-accent-primary hover:bg-accent-primary/90 text-dark-900 dark:text-accent-on-primary font-medium px-6 py-2 rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {fetching ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-dark-900 dark:border-accent-on-primary" />
                  Fetching...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 4V20M17 4V20M3 8H7M17 8H21M3 12H21M3 16H7M17 16H21M7 20H17" />
                  </svg>
                  Get Transcript
                </>
              )}
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex flex-wrap gap-2 mb-4">
              <button
                onClick={() => setBulkMode('csv')}
                className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                  bulkMode === 'csv'
                    ? 'bg-surface-hover text-text-primary border border-accent-primary/12'
                    : 'text-text-muted hover:text-text-primary'
                }`}
              >
                CSV Upload
              </button>
              <button
                onClick={() => setBulkMode('json')}
                className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                  bulkMode === 'json'
                    ? 'bg-surface-hover text-text-primary border border-accent-primary/12'
                    : 'text-text-muted hover:text-text-primary'
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
                  className={`border-2 border-dashed rounded-xl p-6 sm:p-8 text-center cursor-pointer transition-all ${
                    isDragging
                      ? 'border-accent-primary bg-accent-primary/5'
                      : csvFile
                        ? 'border-green-500/30 bg-green-500/5'
                        : 'border-accent-primary/12 hover:border-accent-primary/15 bg-dark-800/50'
                  }`}
                >
                  {csvFile ? (
                    <div className="space-y-2">
                      <svg className="w-8 h-8 text-green-400 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <p className="text-text-primary font-medium">{csvFile.name}</p>
                      <p className="text-text-muted text-sm">{(csvFile.size / 1024).toFixed(1)} KB</p>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <svg className="w-8 h-8 text-text-muted mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                      </svg>
                      <p className="text-text-body">Drop CSV file here or click to browse</p>
                      <p className="text-neutral-500 text-xs">Columns: Video_URL, Video_URL1...Video_URL4, Product Name (optional), Barcode (optional). Duplicate URLs auto-removed.</p>
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
                <label className="block text-sm text-text-muted mb-1.5">JSON Array</label>
                <textarea
                  value={jsonInput}
                  onChange={(e) => setJsonInput(e.target.value)}
                  placeholder={'[\n  { "video_url": "https://www.youtube.com/watch?v=abc123", "product_name": "Product 1", "barcode": "123456" },\n  { "video_url": "https://www.youtube.com/watch?v=def456" }\n]'}
                  rows={6}
                  className="w-full bg-dark-800 border border-accent-primary/12 text-text-primary rounded-lg px-4 py-3 focus:border-accent-primary focus:outline-none placeholder:text-neutral-500 font-mono text-sm"
                />
              </div>
            )}

            <button
              onClick={handleBulkFetch}
              disabled={fetching || (bulkMode === 'csv' ? !csvFile : !jsonInput.trim())}
              className="w-full sm:w-auto bg-accent-primary hover:bg-accent-primary/90 text-dark-900 dark:text-accent-on-primary font-medium px-6 py-2 rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {fetching ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-dark-900 dark:border-accent-on-primary" />
                  Starting...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                  Start Fetching
                </>
              )}
            </button>
          </div>
        )}
      </div>

      <div className="bg-surface-card border border-accent-primary/8 rounded-xl p-4 sm:p-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
          <h2 className="text-lg font-semibold text-text-primary">Transcript Jobs</h2>
          <button
            onClick={loadJobs}
            className="w-full sm:w-auto bg-dark-800 hover:bg-surface-hover text-text-body px-3 py-1.5 rounded-lg text-sm transition-all flex items-center justify-center gap-1.5"
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
            <svg className="w-12 h-12 text-text-faded mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 4V20M17 4V20M3 8H7M17 8H21M3 12H21M3 16H7M17 16H21M7 20H17" />
            </svg>
            <p className="text-text-muted">No transcript jobs yet</p>
            <p className="text-neutral-500 text-sm mt-1">Start by adding a YouTube video URL above</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px]">
              <thead>
                <tr className="text-left text-xs text-text-muted uppercase tracking-wider border-b border-accent-primary/8">
                  <th className="pb-3 pr-4">Status</th>
                  <th className="pb-3 pr-4">Total Videos</th>
                  <th className="pb-3 pr-4">Completed</th>
                  <th className="pb-3 pr-4">Failed</th>
                  <th className="pb-3 pr-4">Date</th>
                  <th className="pb-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-accent-primary/8">
                {jobs.map((job) => (
                  <tr key={job.id} className="group">
                    <td className="py-3 pr-4">{getStatusBadge(job.status)}</td>
                    <td className="py-3 pr-4 text-sm text-text-body">{job.total_videos}</td>
                    <td className="py-3 pr-4 text-sm text-green-400">{job.completed_videos}</td>
                    <td className="py-3 pr-4 text-sm text-text-body">{job.failed_videos}</td>
                    <td className="py-3 pr-4 text-sm text-text-muted">{formatDate(job.created_at)}</td>
                    <td className="py-3 text-right">
                      <div className="flex items-center justify-end gap-2">
                        {job.status === 'running' && (
                          <button
                            onClick={() => handleStop(job.id)}
                            className="bg-red-500/10 hover:bg-red-500/20 text-red-400 px-3 py-1.5 rounded-lg text-xs font-medium transition-all border border-red-500/20"
                          >
                            Stop
                          </button>
                        )}
                        <button
                          onClick={() => handleViewResults(job.id)}
                          className="text-text-muted hover:text-text-primary text-sm transition-all"
                        >
                          {expandedJobId === job.id ? 'Hide' : 'View'}
                        </button>
                        <button
                          onClick={() => handleDownload(job.id)}
                          className="text-text-muted hover:text-text-primary transition-all"
                          title="Download results"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                          </svg>
                        </button>
                        <button
                          onClick={() => handleDeleteRequest(job.id)}
                          className="text-text-muted hover:text-red-400 transition-all"
                          title="Delete job"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
        <div className="bg-surface-card border border-accent-primary/8 rounded-xl p-4 sm:p-6">
          <h3 className="text-lg font-semibold text-text-primary mb-4">
            Job Results
            {jobDetail && (
              <span className="text-sm text-text-muted font-normal ml-2">
                ({jobDetail.results.length} video{jobDetail.results.length !== 1 ? 's' : ''})
              </span>
            )}
          </h3>
          {detailLoading ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-accent-primary" />
            </div>
          ) : jobDetail ? (
            <div className="space-y-3">
              {jobDetail.results.map(renderTranscriptResult)}
            </div>
          ) : null}
        </div>
      )}

      <ConfirmDialog
        open={deleteJobId !== null}
        title="Gorevi Sil"
        message="Bu gorevi silmek istediginizden emin misiniz?"
        confirmLabel="Sil"
        cancelLabel="Iptal"
        variant="danger"
        onConfirm={handleDeleteConfirm}
        onCancel={() => setDeleteJobId(null)}
      />
    </div>
  );
}
