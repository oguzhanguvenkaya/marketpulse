import type { UsePriceMonitorReturn } from '../../hooks/usePriceMonitor';

export default function PriceMonitorFilters({
  platform,
  setPlatform,
  setShowImportModal,
  fetchTaskId,
  fetchStatus,
  fetchProgress,
  currentFetchType,
  handleStopFetch,
  showFetchMenu,
  setShowFetchMenu,
  activeTotalCount,
  inactiveTotalCount,
  lastInactiveCount,
  handleFetchAll,
  showExportMenu,
  setShowExportMenu,
  exportLoading,
  totalProducts,
  handleExport,
  setShowDeleteModal,
}: UsePriceMonitorReturn) {
  return (
    <>
      <div className="flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
        <div>
          <h1 className="text-xl md:text-2xl font-bold text-[#0f1419]">Price Monitor</h1>
          <p className="text-sm md:text-base text-[#9e8b66] mt-1">Track seller prices and identify violations</p>
        </div>
        <div className="flex flex-wrap gap-2 md:gap-3">
          <button onClick={() => setShowImportModal(true)} className="btn-secondary flex items-center gap-2">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Add SKU
          </button>
          {fetchTaskId ? (
            <>
              <div className="px-3 py-2 rounded-lg bg-accent-primary/10 border border-accent-primary/20 text-accent-primary text-xs md:text-sm flex items-center gap-2 w-full sm:w-auto">
                <div className="w-2 h-2 rounded-full bg-accent-primary animate-pulse" />
                {fetchStatus === 'stopping' ? 'Stopping...' : `Fetching ${currentFetchType === 'last_inactive' ? 'last inactive' : currentFetchType}... (${fetchProgress.completed}/${fetchProgress.total})`}
              </div>
              <button onClick={handleStopFetch} disabled={fetchStatus === 'stopping'} className="btn-danger">
                Stop
              </button>
            </>
          ) : (
            <div className="relative">
              <button
                onClick={(e) => { e.stopPropagation(); setShowFetchMenu(!showFetchMenu); }}
                disabled={activeTotalCount === 0 && inactiveTotalCount === 0 && lastInactiveCount === 0}
                className="btn-primary flex items-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Fetch Prices
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>
              {showFetchMenu && (
                <div className="absolute right-0 mt-2 w-56 max-w-[calc(100vw-2rem)] card-dark border border-[#5b4824]/12 z-20 overflow-hidden">
                  <button
                    onClick={() => handleFetchAll('active')}
                    disabled={activeTotalCount === 0}
                    className="w-full text-left px-4 py-3 text-sm text-[#3d3427] hover:bg-[#5b4824]/5 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <div className="font-medium">Active Products</div>
                    <div className="text-xs text-[#9e8b66]">{activeTotalCount} products</div>
                  </button>
                  <button
                    onClick={() => handleFetchAll('last_inactive')}
                    disabled={lastInactiveCount === 0}
                    className="w-full text-left px-4 py-3 text-sm text-[#3d3427] hover:bg-[#5b4824]/5 transition-colors border-t border-[#5b4824]/8 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <div className="font-medium text-orange-400">Last Inactive</div>
                    <div className="text-xs text-[#9e8b66]">{lastInactiveCount} SKUs from last fetch</div>
                  </button>
                  <button
                    onClick={() => handleFetchAll('inactive')}
                    disabled={inactiveTotalCount === 0}
                    className="w-full text-left px-4 py-3 text-sm text-[#3d3427] hover:bg-[#5b4824]/5 transition-colors border-t border-[#5b4824]/8 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <div className="font-medium text-red-400">All Inactive</div>
                    <div className="text-xs text-[#9e8b66]">{inactiveTotalCount} products</div>
                  </button>
                </div>
              )}
            </div>
          )}
          <div className="relative">
            <button
              onClick={(e) => { e.stopPropagation(); setShowExportMenu(!showExportMenu); }}
              disabled={exportLoading || totalProducts === 0}
              className="btn-secondary flex items-center gap-2"
            >
              {exportLoading ? 'Exporting...' : 'Export'}
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            {showExportMenu && (
              <div className="absolute right-0 mt-2 w-48 max-w-[calc(100vw-2rem)] card-dark border border-[#5b4824]/12 z-20 overflow-hidden">
                <button onClick={() => handleExport('all')} className="w-full text-left px-4 py-3 text-sm text-[#3d3427] hover:bg-[#5b4824]/5 transition-colors">
                  All ({totalProducts})
                </button>
                <button onClick={() => handleExport('active')} className="w-full text-left px-4 py-3 text-sm text-[#3d3427] hover:bg-[#5b4824]/5 transition-colors">
                  Active Only ({activeTotalCount})
                </button>
                <button onClick={() => handleExport('inactive')} className="w-full text-left px-4 py-3 text-sm text-[#3d3427] hover:bg-[#5b4824]/5 transition-colors">
                  Inactive Only ({inactiveTotalCount})
                </button>
              </div>
            )}
          </div>
          <button
            onClick={() => setShowDeleteModal('inactive')}
            disabled={inactiveTotalCount === 0}
            className="btn-secondary text-orange-400 border-orange-400/30 hover:bg-orange-500/10 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Delete Inactive
          </button>
          <button
            onClick={() => setShowDeleteModal('all')}
            disabled={totalProducts === 0}
            className="btn-secondary text-red-400 border-red-400/30 hover:bg-red-500/10 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Delete All
          </button>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => setPlatform('hepsiburada')}
          className={`px-4 py-2 rounded-lg font-medium text-sm transition-all ${
            platform === 'hepsiburada'
              ? 'bg-[#ff6000] text-[#0f1419] shadow-glow-orange'
              : 'bg-[#f0e8d8] text-[#5f471d] hover:bg-[#e8dfcf]'
          }`}
        >
          Hepsiburada
        </button>
        <button
          onClick={() => setPlatform('trendyol')}
          className={`px-4 py-2 rounded-lg font-medium text-sm transition-all ${
            platform === 'trendyol'
              ? 'bg-[#ff6000] text-[#0f1419] shadow-glow-orange'
              : 'bg-[#f0e8d8] text-[#5f471d] hover:bg-[#e8dfcf]'
          }`}
        >
          Trendyol
        </button>
      </div>
    </>
  );
}
