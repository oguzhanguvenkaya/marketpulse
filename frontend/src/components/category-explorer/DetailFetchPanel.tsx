import type { UseCategoryExplorerReturn } from '../../hooks/useCategoryExplorer';

export default function DetailFetchPanel({
  showDetailPanel,
  viewMode,
  detailStats,
  selectedForDetail,
  detailFetching,
  detailProgress,
  selectAllForDetail,
  handleBulkDelete,
  handleFetchDetails,
}: UseCategoryExplorerReturn) {
  if (!showDetailPanel || viewMode !== 'category_page') return null;

  return (
    <div className="rounded-xl border border-[#9e8b66]/15 dark:border-[#6B8F80]/15 overflow-hidden bg-gradient-to-br from-[#5b4824]/5 to-[#5b4824]/3 dark:from-[#4ADE80]/5 dark:to-[#4ADE80]/3">
      <div className="p-4 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <svg className="w-4 h-4 text-[#9e8b66] dark:text-[#6B8F80]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
            <span className="text-sm font-medium text-purple-300">Get Product Details</span>
            <span className="text-[10px] text-neutral-500">Step 2: Fetch detailed data for selected products</span>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
          <div className="flex items-center gap-3 text-xs">
            <span className="text-[#9e8b66] dark:text-[#6B8F80]">
              <span className="text-[#0f1419] dark:text-[#F0FDF4] font-medium">{detailStats.total}</span> products
            </span>
            <span className="text-emerald-600">
              <span className="font-medium">{detailStats.fetched}</span> detailed
            </span>
            <span className="text-amber-400">
              <span className="font-medium">{detailStats.unfetched}</span> pending
            </span>
            <span className="text-[#5b4824] dark:text-[#4ADE80]">
              <span className="font-medium">{selectedForDetail.size}</span> selected
            </span>
          </div>

          <div className="flex items-center gap-2 sm:ml-auto">
            <button
              onClick={selectAllForDetail}
              className="px-3 py-1.5 text-xs rounded-lg border border-[#5b4824]/12 dark:border-[#4ADE80]/12 text-[#5f471d] dark:text-[#A7C4B8] hover:bg-[#5b4824]/8 dark:hover:bg-[#4ADE80]/8 transition-colors flex items-center gap-1.5"
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
              </svg>
              {selectedForDetail.size === detailStats.unfetched && detailStats.unfetched > 0 ? 'Deselect All' : `Select All (${detailStats.unfetched})`}
            </button>
            {selectedForDetail.size > 0 && (
              <button
                onClick={handleBulkDelete}
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
                <div className="w-3 h-3 border-2 border-[#5b4824]/20 dark:border-[#4ADE80]/20 border-t-[#5b4824] dark:border-t-[#4ADE80] rounded-full animate-spin" />
              ) : (
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
              )}
              {detailFetching ? 'Fetching...' : `Fetch Details (${selectedForDetail.size})`}
            </button>
          </div>
        </div>

        {detailProgress && (
          <div className={`flex items-center gap-2 text-xs ${detailProgress.includes('failed') ? 'text-red-600' : detailProgress.includes('All details') ? 'text-emerald-600' : 'text-[#9e8b66] dark:text-[#6B8F80]'}`}>
            {detailFetching && <div className="w-3 h-3 border-2 border-[#9e8b66]/30 dark:border-[#6B8F80]/30 border-t-[#9e8b66] dark:border-t-[#6B8F80] rounded-full animate-spin" />}
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
