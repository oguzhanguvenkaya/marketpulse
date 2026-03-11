import type { UseMyStoreReturn } from '../../hooks/useMyStore';

const PLATFORM_TABS: { key: 'all' | 'web' | 'hepsiburada' | 'trendyol'; label: string; color: string }[] = [
  { key: 'all', label: 'Tümü', color: 'bg-accent-primary' },
  { key: 'hepsiburada', label: 'Hepsiburada', color: 'bg-[#ff6000]' },
  { key: 'trendyol', label: 'Trendyol', color: 'bg-[#f27a1a]' },
  { key: 'web', label: 'Web', color: 'bg-blue-500' },
];

export default function MyStoreHeader(props: UseMyStoreReturn) {
  const { platformFilter, setPlatformFilter, setShowImportModal, stats, totalProducts, setShowDeleteAllModal } = props;

  return (
    <div className="space-y-4">
      {/* Title + Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Mağazam</h1>
          <p className="text-sm text-text-muted">Platformlar arası ürün karşılaştırma</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowImportModal(true)}
            className="btn-primary px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
            CSV Import
          </button>
          {totalProducts > 0 && (
            <button
              onClick={() => setShowDeleteAllModal(true)}
              className="px-4 py-2 rounded-lg text-sm font-medium text-danger border border-danger/30 hover:bg-danger/10 transition-colors"
            >
              Tümünü Sil
            </button>
          )}
        </div>
      </div>

      {/* Platform Tabs + Stats */}
      <div className="flex flex-col sm:flex-row sm:items-center gap-3">
        <div className="flex items-center gap-2">
          {PLATFORM_TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setPlatformFilter(tab.key)}
              className={`px-4 py-2 rounded-lg font-medium text-sm transition-all ${
                platformFilter === tab.key
                  ? `${tab.color} text-white shadow-md`
                  : 'bg-surface-hover text-text-body hover:bg-surface-hover-active'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-3 text-xs text-text-muted ml-auto">
          <span className="px-2 py-1 rounded bg-blue-500/10 text-blue-400">Web: {stats.web_count}</span>
          <span className="px-2 py-1 rounded bg-[#ff6000]/10 text-[#ff6000]">HB: {stats.hb_matched}</span>
          <span className="px-2 py-1 rounded bg-[#f27a1a]/10 text-[#f27a1a]">TY: {stats.ty_matched}</span>
        </div>
      </div>
    </div>
  );
}
