import type { UsePriceMonitorReturn } from '../../hooks/usePriceMonitor';

export default function ImportModal({
  platform,
  setShowImportModal,
  importJson,
  setImportJson,
  importLoading,
  handleImport,
  getImportExample,
}: UsePriceMonitorReturn) {
  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4 overflow-y-auto">
      <div className="card-dark border border-[#5b4824]/12 dark:border-[#4ADE80]/12 p-5 md:p-6 w-full max-w-2xl mx-auto my-auto">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-[#0f1419] dark:text-[#F0FDF4]">
            Import Products - {platform === 'hepsiburada' ? 'Hepsiburada' : 'Trendyol'}
          </h3>
          <button
            onClick={() => { setShowImportModal(false); setImportJson(''); }}
            className="text-[#9e8b66] dark:text-[#6B8F80] hover:text-[#0f1419] dark:hover:text-[#F0FDF4] transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <p className="text-sm text-[#9e8b66] dark:text-[#6B8F80] mb-3">Paste JSON in the following format:</p>
        <pre className="bg-[#fffbef] dark:bg-[#0F1A17] p-3 rounded-lg text-xs text-[#5f471d] dark:text-[#A7C4B8] mb-4 overflow-x-auto border border-[#5b4824]/8 dark:border-[#4ADE80]/8">
          {getImportExample()}
        </pre>
        <textarea
          value={importJson}
          onChange={(e) => setImportJson(e.target.value)}
          className="input-dark w-full h-48 font-mono text-sm resize-none"
          placeholder='[{"productUrl": "...", "sku": "..."}]'
        />
        <div className="flex flex-col-reverse sm:flex-row sm:justify-end gap-3 mt-4">
          <button
            onClick={() => { setShowImportModal(false); setImportJson(''); }}
            className="btn-secondary"
          >
            Cancel
          </button>
          <button
            onClick={handleImport}
            disabled={importLoading || !importJson.trim()}
            className="btn-primary"
          >
            {importLoading ? 'Importing...' : 'Import'}
          </button>
        </div>
      </div>
    </div>
  );
}
