import type { UseCategoryExplorerReturn } from '../../hooks/useCategoryExplorer';

export default function DetailFetchPanel({
  showDetailPanel,
  viewMode,
  detailStats,
  selectedForDetail,
  detailFetching,
  detailProgress,
  selectAllForDetail,
  handleBulkDeleteRequest,
  handleFetchDetails,
}: UseCategoryExplorerReturn) {
  if (!showDetailPanel || viewMode !== 'category_page') return null;

  return (
    <div className="rounded-xl border border-text-muted/15 overflow-hidden bg-gradient-to-br from-accent-primary/5 to-accent-primary/3">
      <div className="p-4 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <svg className="w-4 h-4 text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
            <span className="text-sm font-medium text-purple-300">Get Product Details</span>
            <span className="text-[10px] text-neutral-500 dark:text-text-muted">Step 2: Fetch detailed data for selected products</span>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
          <div className="flex items-center gap-3 text-xs">
            <span className="text-text-muted">
              <span className="text-text-primary font-medium">{detailStats.total}</span> products
            </span>
            <span className="text-emerald-600">
              <span className="font-medium">{detailStats.fetched}</span> detailed
            </span>
            <span className="text-amber-400">
              <span className="font-medium">{detailStats.unfetched}</span> pending
            </span>
            <span className="text-accent-primary">
              <span className="font-medium">{selectedForDetail.size}</span> selected
            </span>
          </div>

          <div className="flex items-center gap-2 sm:ml-auto">
            <button
              onClick={selectAllForDetail}
              className="px-3 py-1.5 text-xs rounded-lg border border-accent-primary/12 text-text-body hover:bg-accent-primary/8 transition-colors flex items-center gap-1.5"
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
              </svg>
              {selectedForDetail.size === detailStats.unfetched && detailStats.unfetched > 0 ? 'Deselect All' : `Select All (${detailStats.unfetched})`}
            </button>
            {selectedForDetail.size > 0 && (
              <button
                onClick={handleBulkDeleteRequest}
                className="px-3 py-1.5 text-xs rounded-lg border border-red-500/30 text-red-600 hover:bg-red-500/20 transition-colors flex items-center gap-1.5"
              >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                Delete ({selectedForDetail.size})
              </button>
            )}
            <button
              onClick={handleFetchDetails}
              disabled={detailFetching || selectedForDetail.size === 0}
              className={`px-4 py-1.5 text-xs rounded-lg text-[#0f1419] dark:text-[#0F1A17] font-medium disabled:opacity-50 flex items-center gap-2 whitespace-nowrap ${detailFetching ? 'bg-[#d4cfc1] dark:bg-[#1C2E28]' : 'bg-gradient-to-br from-[#9e8b66] to-[#5b4824] dark:from-[#4ADE80] dark:to-[#166534]'}`}
            >
              {detailFetching ? (
                <div className="w-3 h-3 border-2 border-accent-primary/20 border-t-accent-primary rounded-full animate-spin" />
              ) : (
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
              )}
              {detailFetching ? 'Fetching...' : `Fetch Details (${selectedForDetail.size})`}
            </button>
          </div>
        </div>

        {detailProgress && (
          <div className={`flex items-center gap-2 text-xs ${detailProgress.includes('failed') ? 'text-red-600' : detailProgress.includes('All details') ? 'text-emerald-600' : 'text-text-muted'}`}>
            {detailFetching && <div className="w-3 h-3 border-2 border-text-muted/30 border-t-text-muted rounded-full animate-spin" />}
            {!detailFetching && detailProgress.includes('All details') && (
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
            )}
            {detailProgress}
          </div>
        )}
      </div>
    </div>
  );
}
