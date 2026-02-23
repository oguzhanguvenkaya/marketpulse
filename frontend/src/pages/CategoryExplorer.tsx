import { useCategoryExplorer } from '../hooks/useCategoryExplorer';
import CategoryFilters from '../components/category-explorer/CategoryFilters';
import ProductCards from '../components/category-explorer/ProductCards';
import ScraperPanel from '../components/category-explorer/ScraperPanel';
import DetailFetchPanel from '../components/category-explorer/DetailFetchPanel';
import ProductDetailModals from '../components/category-explorer/ProductDetailModal';
import ConfirmDialog from '../components/ConfirmDialog';

export default function CategoryExplorer() {
  const ce = useCategoryExplorer();
  const {
    viewMode, setViewMode,
    showScraper, setShowScraper,
    showDetailPanel, setShowDetailPanel,
    setSelectedForDetail,
    setShowMobileFilters,
    breadcrumbParts,
    setSelectedCategory,
    setExpandedCategories,
    selectCategory,
    search, setSearch,
    sortBy, sortDir, setSortBy, setSortDir,
    catSortBy, catSortDir, setCatSortBy, setCatSortDir,
    dynamicStats,
    formatPrice,
    catFilterData,
    catBrand, setCatBrand,
    catSeller, setCatSeller,
    catMinPrice, setCatMinPrice,
    catMaxPrice, setCatMaxPrice,
    catMinRating, setCatMinRating,
    catSponsored, setCatSponsored,
  } = ce;

  return (
    <div className="flex gap-6 pb-10 min-h-[calc(100vh-80px)]">
      <aside className="hidden lg:block w-64 flex-shrink-0">
        <div className="sticky top-4 rounded-xl border border-[#5b4824]/12 dark:border-[#4ADE80]/12 p-4 overflow-hidden bg-gradient-to-b from-[#fefbf0] to-[#fffbef] dark:from-[#162420] dark:to-[#0F1A17]">
          <CategoryFilters {...ce} />
        </div>
      </aside>

      <main className="flex-1 min-w-0 space-y-5">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-xs text-neutral-500 uppercase tracking-wider mb-1">Competitive Analysis</div>
            <h1 className="text-2xl font-bold text-[#0f1419] dark:text-[#F0FDF4]">Category Explorer</h1>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={() => setShowMobileFilters(true)}
              className="lg:hidden px-3 py-2 text-sm rounded-lg border border-[#5b4824]/12 dark:border-[#4ADE80]/12 text-[#5f471d] dark:text-[#A7C4B8] hover:bg-[#5b4824]/5 dark:hover:bg-[#4ADE80]/5">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" /></svg>
            </button>
            {viewMode === 'category_page' && (
              <button
                onClick={() => { setShowDetailPanel(!showDetailPanel); setSelectedForDetail(new Set()); }}
                className={`px-3 py-2 text-sm rounded-lg border transition-colors flex items-center gap-1.5 ${
                  showDetailPanel ? 'border-[#9e8b66]/20 dark:border-[#6B8F80]/20 bg-[#9e8b66]/8 dark:bg-[#6B8F80]/8 text-[#9e8b66] dark:text-[#6B8F80]' : 'border-[#5b4824]/12 dark:border-[#4ADE80]/12 text-[#5f471d] dark:text-[#A7C4B8] hover:bg-[#5b4824]/5 dark:hover:bg-[#4ADE80]/5'
                }`}
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
                </svg>
                Get Details
              </button>
            )}
            <button
              onClick={() => setShowScraper(!showScraper)}
              className={`px-3 py-2 text-sm rounded-lg border transition-colors flex items-center gap-1.5 ${
                showScraper ? 'border-[#5b4824]/20 dark:border-[#4ADE80]/20 bg-[#5b4824]/8 dark:bg-[#4ADE80]/8 text-[#5b4824] dark:text-[#4ADE80]' : 'border-[#5b4824]/12 dark:border-[#4ADE80]/12 text-[#5f471d] dark:text-[#A7C4B8] hover:bg-[#5b4824]/5 dark:hover:bg-[#4ADE80]/5'
              }`}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
              </svg>
              Scrape New
            </button>
          </div>
        </div>

        <ScraperPanel {...ce} />
        <DetailFetchPanel {...ce} />

        <div className="flex items-center gap-1 p-1 rounded-xl bg-[#5b4824]/5 dark:bg-[#4ADE80]/5 w-fit">
          <button
            onClick={() => setViewMode('my_products')}
            className={`px-4 py-2 text-sm rounded-lg font-medium transition-colors ${
              viewMode === 'my_products' ? 'bg-[#5b4824]/8 dark:bg-[#4ADE80]/8 text-[#0f1419] dark:text-[#F0FDF4] shadow-sm' : 'text-[#9e8b66] dark:text-[#6B8F80] hover:text-[#3d3427] dark:hover:text-[#F0FDF4]'
            }`}
          >
            <span className="flex items-center gap-1.5">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" /></svg>
              My Products
            </span>
          </button>
          <button
            onClick={() => setViewMode('category_page')}
            className={`px-4 py-2 text-sm rounded-lg font-medium transition-colors ${
              viewMode === 'category_page' ? 'bg-[#5b4824]/8 dark:bg-[#4ADE80]/8 text-[#0f1419] dark:text-[#F0FDF4] shadow-sm' : 'text-[#9e8b66] dark:text-[#6B8F80] hover:text-[#3d3427] dark:hover:text-[#F0FDF4]'
            }`}
          >
            <span className="flex items-center gap-1.5">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" /></svg>
              Category Page
            </span>
          </button>
        </div>

        {breadcrumbParts.length > 0 && (
          <div className="flex items-center gap-1.5 text-sm flex-wrap">
            <button onClick={() => setSelectedCategory('')} className="text-neutral-500 hover:text-[#5b4824] dark:hover:text-[#4ADE80] transition-colors">All</button>
            {breadcrumbParts.map((bc, i) => (
              <span key={i} className="flex items-center gap-1.5">
                <svg className="w-3 h-3 text-[#b5a382] dark:text-[#6B8F80]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" /></svg>
                <button onClick={() => selectCategory(bc.path)}
                  className={`hover:text-[#5b4824] dark:hover:text-[#4ADE80] transition-colors ${i === breadcrumbParts.length - 1 ? 'text-[#5b4824] dark:text-[#4ADE80] font-medium' : 'text-[#9e8b66] dark:text-[#6B8F80]'}`}>
                  {bc.name}
                </button>
              </span>
            ))}
            <button onClick={() => { setSelectedCategory(''); setExpandedCategories(new Set()); }} className="ml-2 text-[#b5a382] dark:text-[#6B8F80] hover:text-red-600 transition-colors">
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
            </button>
          </div>
        )}

        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
          <div className="relative flex-1 w-full sm:w-auto">
            <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              type="text" value={search} onChange={(e) => setSearch(e.target.value)}
              placeholder="Search products, brands, SKU..."
              className="w-full bg-[#f7eede] dark:bg-[#1C2E28] border border-[#5b4824]/12 dark:border-[#4ADE80]/12 rounded-lg pl-10 pr-4 py-2.5 text-sm text-[#3d3427] dark:text-[#A7C4B8] placeholder:text-[#b5a382] dark:placeholder:text-[#6B8F80] focus:outline-none focus:border-[#5b4824]/30 dark:focus:border-[#4ADE80]/30"
            />
          </div>
          {viewMode === 'my_products' ? (
            <select
              value={`${sortBy}:${sortDir}`}
              onChange={(e) => { const [s, d] = e.target.value.split(':'); setSortBy(s); setSortDir(d); }}
              className="bg-[#f7eede] dark:bg-[#1C2E28] border border-[#5b4824]/12 dark:border-[#4ADE80]/12 rounded-lg px-3 py-2.5 text-sm text-[#3d3427] dark:text-[#A7C4B8] focus:outline-none focus:border-[#5b4824]/30 dark:focus:border-[#4ADE80]/30"
            >
              <option value="created_at:desc">Newest First</option>
              <option value="created_at:asc">Oldest First</option>
              <option value="price:asc">Price: Low to High</option>
              <option value="price:desc">Price: High to Low</option>
              <option value="rating:desc">Highest Rated</option>
              <option value="product_name:asc">Name A-Z</option>
            </select>
          ) : (
            <select
              value={`${catSortBy}:${catSortDir}`}
              onChange={(e) => { const [s, d] = e.target.value.split(':'); setCatSortBy(s); setCatSortDir(d); }}
              className="bg-[#f7eede] dark:bg-[#1C2E28] border border-[#5b4824]/12 dark:border-[#4ADE80]/12 rounded-lg px-3 py-2.5 text-sm text-[#3d3427] dark:text-[#A7C4B8] focus:outline-none focus:border-[#5b4824]/30 dark:focus:border-[#4ADE80]/30"
            >
              <option value="position:asc">Marketplace Position</option>
              <option value="created_at:desc">Newest First</option>
              <option value="price:asc">Price: Low to High</option>
              <option value="price:desc">Price: High to Low</option>
              <option value="rating:desc">Highest Rated</option>
              <option value="name:asc">Name A-Z</option>
            </select>
          )}
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-1.5 text-center">
          <div className="rounded-lg border border-[#5b4824]/8 dark:border-[#4ADE80]/8 p-3 bg-[#5b4824]/[0.03] dark:bg-[#4ADE80]/[0.03]">
            <div className="text-lg font-bold text-[#0f1419] dark:text-[#F0FDF4]">{dynamicStats.total.toLocaleString()}</div>
            <div className="text-xs text-neutral-500">Products</div>
          </div>
          <div className="rounded-lg border border-[#5b4824]/8 dark:border-[#4ADE80]/8 p-3 bg-[#5b4824]/[0.03] dark:bg-[#4ADE80]/[0.03]">
            <div className="text-lg font-bold text-[#5b4824] dark:text-[#4ADE80]">{formatPrice(dynamicStats.avgPrice)}</div>
            <div className="text-xs text-neutral-500">Avg Price</div>
          </div>
          <div className="rounded-lg border border-[#5b4824]/8 dark:border-[#4ADE80]/8 p-3 bg-[#5b4824]/[0.03] dark:bg-[#4ADE80]/[0.03]">
            <div className="text-lg font-bold text-[#9e8b66] dark:text-[#6B8F80]">{dynamicStats.brandCount}</div>
            <div className="text-xs text-neutral-500">Brands</div>
          </div>
          <div className="rounded-lg border border-[#5b4824]/8 dark:border-[#4ADE80]/8 p-3 bg-[#5b4824]/[0.03] dark:bg-[#4ADE80]/[0.03]">
            {viewMode === 'category_page' ? (
              <>
                <div className="text-sm font-bold text-emerald-600">
                  {dynamicStats.lastScraped ? new Date(dynamicStats.lastScraped).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '-'}
                </div>
                <div className="text-xs text-neutral-500">Last Scraped</div>
              </>
            ) : (
              <>
                <div className="text-lg font-bold text-emerald-600">{dynamicStats.categoryCount}</div>
                <div className="text-xs text-neutral-500">Categories</div>
              </>
            )}
          </div>
        </div>

        {viewMode === 'category_page' && (
          <div className="flex flex-wrap items-end gap-2">
            <div className="flex-1 min-w-[140px]">
              <label className="text-[10px] text-neutral-500 uppercase tracking-wider mb-1 block">Brand</label>
              <select value={catBrand} onChange={e => setCatBrand(e.target.value)}
                className="w-full bg-[#f7eede] dark:bg-[#1C2E28] border border-[#5b4824]/12 dark:border-[#4ADE80]/12 rounded-lg px-2.5 py-2 text-sm text-[#3d3427] dark:text-[#A7C4B8] focus:outline-none focus:border-[#5b4824]/30 dark:focus:border-[#4ADE80]/30">
                <option value="">All Brands</option>
                {(catFilterData?.brands || []).map(b => <option key={b} value={b}>{b}</option>)}
              </select>
            </div>
            <div className="flex-1 min-w-[140px]">
              <label className="text-[10px] text-neutral-500 uppercase tracking-wider mb-1 block">Seller</label>
              <select value={catSeller} onChange={e => setCatSeller(e.target.value)}
                className="w-full bg-[#f7eede] dark:bg-[#1C2E28] border border-[#5b4824]/12 dark:border-[#4ADE80]/12 rounded-lg px-2.5 py-2 text-sm text-[#3d3427] dark:text-[#A7C4B8] focus:outline-none focus:border-[#5b4824]/30 dark:focus:border-[#4ADE80]/30">
                <option value="">All Sellers</option>
                {(catFilterData?.sellers || []).map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div className="min-w-[100px]">
              <label className="text-[10px] text-neutral-500 uppercase tracking-wider mb-1 block">Min Price</label>
              <input type="number" value={catMinPrice} onChange={e => setCatMinPrice(e.target.value)} placeholder="Min"
                className="w-full bg-[#f7eede] dark:bg-[#1C2E28] border border-[#5b4824]/12 dark:border-[#4ADE80]/12 rounded-lg px-2.5 py-2 text-sm text-[#3d3427] dark:text-[#A7C4B8] focus:outline-none focus:border-[#5b4824]/30 dark:focus:border-[#4ADE80]/30" />
            </div>
            <div className="min-w-[100px]">
              <label className="text-[10px] text-neutral-500 uppercase tracking-wider mb-1 block">Max Price</label>
              <input type="number" value={catMaxPrice} onChange={e => setCatMaxPrice(e.target.value)} placeholder="Max"
                className="w-full bg-[#f7eede] dark:bg-[#1C2E28] border border-[#5b4824]/12 dark:border-[#4ADE80]/12 rounded-lg px-2.5 py-2 text-sm text-[#3d3427] dark:text-[#A7C4B8] focus:outline-none focus:border-[#5b4824]/30 dark:focus:border-[#4ADE80]/30" />
            </div>
            <div className="min-w-[80px]">
              <label className="text-[10px] text-neutral-500 uppercase tracking-wider mb-1 block">Min Rating</label>
              <select value={catMinRating} onChange={e => setCatMinRating(e.target.value)}
                className="w-full bg-[#f7eede] dark:bg-[#1C2E28] border border-[#5b4824]/12 dark:border-[#4ADE80]/12 rounded-lg px-2.5 py-2 text-sm text-[#3d3427] dark:text-[#A7C4B8] focus:outline-none focus:border-[#5b4824]/30 dark:focus:border-[#4ADE80]/30">
                <option value="">Any</option>
                <option value="4">4+</option>
                <option value="3">3+</option>
                <option value="2">2+</option>
              </select>
            </div>
            <div className="min-w-[100px]">
              <label className="text-[10px] text-neutral-500 uppercase tracking-wider mb-1 block">Sponsored</label>
              <select value={catSponsored} onChange={e => setCatSponsored(e.target.value as '' | 'true' | 'false')}
                className="w-full bg-[#f7eede] dark:bg-[#1C2E28] border border-[#5b4824]/12 dark:border-[#4ADE80]/12 rounded-lg px-2.5 py-2 text-sm text-[#3d3427] dark:text-[#A7C4B8] focus:outline-none focus:border-[#5b4824]/30 dark:focus:border-[#4ADE80]/30">
                <option value="">All</option>
                <option value="true">Sponsored Only</option>
                <option value="false">Non-Sponsored</option>
              </select>
            </div>
            {(catBrand || catSeller || catMinPrice || catMaxPrice || catMinRating || catSponsored) && (
              <button
                onClick={() => { setCatBrand(''); setCatSeller(''); setCatMinPrice(''); setCatMaxPrice(''); setCatMinRating(''); setCatSponsored(''); }}
                className="text-xs text-[#9e8b66] dark:text-[#6B8F80] hover:text-red-600 px-2 py-2 transition-colors whitespace-nowrap"
              >
                Clear Filters
              </button>
            )}
          </div>
        )}

        <ProductCards {...ce} />
      </main>

      <ProductDetailModals {...ce} />

      <ConfirmDialog
        open={ce.confirmAction !== null}
        title="Silme Onayi"
        message={ce.confirmAction?.message ?? ''}
        confirmLabel="Sil"
        cancelLabel="Iptal"
        variant="danger"
        onConfirm={ce.handleConfirmAction}
        onCancel={ce.handleCancelAction}
      />
    </div>
  );
}
