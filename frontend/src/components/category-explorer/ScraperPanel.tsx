import type { UseCategoryExplorerReturn } from '../../hooks/useCategoryExplorer';

export default function ScraperPanel({
  showScraper,
  scrapeUrl,
  setScrapeUrl,
  scrapePageCount,
  setScrapePageCount,
  scraping,
  scrapeProgress,
  scrapeMsg,
  handleScrape,
}: UseCategoryExplorerReturn) {
  if (!showScraper) return null;

  return (
    <div className="rounded-xl border border-[#5b4824]/10 dark:border-[#4ADE80]/10 overflow-hidden bg-gradient-to-br from-[#f7ce86]/8 to-[#f7ce86]/4 dark:from-[#4ADE80]/8 dark:to-[#4ADE80]/4">
      <div className="p-4 space-y-3">
        <div className="flex items-center gap-2 mb-1">
          <svg className="w-4 h-4 text-[#5b4824] dark:text-[#4ADE80]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
          </svg>
          <span className="text-sm font-medium text-[#5b4824] dark:text-[#4ADE80]">Scrape Category Page</span>
          <span className="text-[10px] text-neutral-500 ml-auto">Step 1: Collect product listings from marketplace</span>
        </div>

        <div className="flex flex-col sm:flex-row gap-3">
          <input
            type="text"
            value={scrapeUrl}
            onChange={(e) => setScrapeUrl(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && !scraping) handleScrape(); }}
            placeholder="Paste category URL — e.g. https://www.hepsiburada.com/hizli-cilalar-c-20035738"
            className="flex-1 bg-[#f7eede] dark:bg-[#1C2E28] border border-[#5b4824]/12 dark:border-[#4ADE80]/12 rounded-lg px-4 py-2.5 text-sm text-[#3d3427] dark:text-[#A7C4B8] placeholder:text-[#b5a382] dark:placeholder:text-[#6B8F80] focus:outline-none focus:border-[#5b4824]/30 dark:focus:border-[#4ADE80]/30"
          />
        </div>

        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
          <div className="flex items-center gap-2">
            <label className="text-xs text-[#9e8b66] dark:text-[#6B8F80] whitespace-nowrap">Pages to scrape:</label>
            <div className="flex items-center gap-1">
              {[1, 2, 3, 5, 10].map(n => (
                <button
                  key={n}
                  onClick={() => setScrapePageCount(n)}
                  className={`px-2.5 py-1 text-xs rounded-md transition-colors ${
                    scrapePageCount === n
                      ? 'bg-[#5b4824]/10 dark:bg-[#4ADE80]/10 text-[#5b4824] dark:text-[#4ADE80] border border-[#5b4824]/20 dark:border-[#4ADE80]/20'
                      : 'bg-[#5b4824]/5 dark:bg-[#4ADE80]/5 text-[#9e8b66] dark:text-[#6B8F80] border border-[#5b4824]/12 dark:border-[#4ADE80]/12 hover:bg-[#5b4824]/8 dark:hover:bg-[#4ADE80]/8'
                  }`}
                >
                  {n}
                </button>
              ))}
              <input
                type="number"
                min={1}
                max={20}
                value={scrapePageCount}
                onChange={(e) => setScrapePageCount(Math.max(1, Math.min(20, parseInt(e.target.value) || 1)))}
                className="w-14 bg-[#f7eede] dark:bg-[#1C2E28] border border-[#5b4824]/12 dark:border-[#4ADE80]/12 rounded-md px-2 py-1 text-xs text-[#3d3427] dark:text-[#A7C4B8] text-center focus:outline-none focus:border-[#5b4824]/30 dark:focus:border-[#4ADE80]/30"
              />
            </div>
          </div>

          <div className="flex items-center gap-2 sm:ml-auto">
            {scrapeUrl && (
              <span className="text-[10px] text-neutral-500">
                {scrapeUrl.includes('hepsiburada') ? 'HB' : scrapeUrl.includes('trendyol') ? 'TY' : 'URL'}
                {scrapePageCount > 1 && ` • ${scrapePageCount} pages: ${
                  scrapeUrl.includes('trendyol') ? '?pi=1...' + scrapePageCount : '?sayfa=1...' + scrapePageCount
                }`}
              </span>
            )}
            <button
              onClick={handleScrape}
              disabled={scraping || !scrapeUrl}
              className={`px-5 py-2 text-sm rounded-lg text-[#0f1419] dark:text-[#0F1A17] font-medium disabled:opacity-50 flex items-center gap-2 whitespace-nowrap ${scraping ? 'bg-[#d4cfc1] dark:bg-[#1C2E28]' : 'bg-gradient-to-br from-[#f7ce86] to-[#5b4824] dark:from-[#4ADE80] dark:to-[#166534]'}`}
            >
              {scraping ? (
                <div className="w-4 h-4 border-2 border-[#5b4824]/20 dark:border-[#4ADE80]/20 border-t-[#5b4824] dark:border-t-[#4ADE80] rounded-full animate-spin" />
              ) : (
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
              )}
              {scraping ? 'Scraping...' : 'Scrape Pages'}
            </button>
          </div>
        </div>

        {scrapeProgress && (
          <div className="flex items-center gap-2 text-xs text-[#5b4824] dark:text-[#4ADE80]">
            <div className="w-3 h-3 border-2 border-[#5b4824]/30 dark:border-[#4ADE80]/30 border-t-[#5b4824] dark:border-t-[#4ADE80] rounded-full animate-spin" />
            {scrapeProgress}
          </div>
        )}
        {scrapeMsg && (
          <p className={`text-xs ${scrapeMsg.includes('fail') || scrapeMsg.includes('Failed') ? 'text-red-600' : 'text-emerald-600'}`}>{scrapeMsg}</p>
        )}
      </div>
    </div>
  );
}
