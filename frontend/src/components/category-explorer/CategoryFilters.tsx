import type { UseCategoryExplorerReturn, Platform } from '../../hooks/useCategoryExplorer';
import CategoryTree from './CategoryTree';

export default function CategoryFilters(ce: UseCategoryExplorerReturn) {
  const {
    platform,
    viewMode,
    filters,
    selectedCategory,
    selectedBrand,
    minPrice,
    maxPrice,
    minRating,
    platformStats,
    handlePlatformChange,
    setSelectedBrand,
    setMinPrice,
    setMaxPrice,
    setMinRating,
    setPage,
    setSelectedCategory,
    setExpandedCategories,
  } = ce;

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-xs font-medium text-neutral-500 uppercase tracking-wider mb-2 px-2">Platform</h3>
        <div className="space-y-0.5">
          {[
            { key: '' as Platform, label: 'All Platforms', count: platformStats.total, color: 'text-text-body' },
            { key: 'hepsiburada' as Platform, label: 'Hepsiburada', count: platformStats.hb, color: 'text-orange-400' },
            { key: 'trendyol' as Platform, label: 'Trendyol', count: platformStats.ty, color: 'text-text-muted' },
            { key: 'web' as Platform, label: 'Web', count: platformStats.web, color: 'text-blue-400' },
          ].map(p => (
            <button
              key={p.key}
              onClick={() => handlePlatformChange(p.key)}
              className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-colors ${
                platform === p.key ? 'bg-accent-primary/8 text-text-primary' : 'text-text-muted hover:bg-accent-primary/5 hover:text-text-secondary'
              }`}
            >
              <span className={platform === p.key ? p.color : ''}>{p.label}</span>
              <span className="text-[10px] text-text-faded">{p.count}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="border-t border-accent-primary/8 pt-3">
        <h3 className="text-xs font-medium text-neutral-500 uppercase tracking-wider mb-2 px-2">Categories</h3>
        <CategoryTree {...ce} />
      </div>

      {viewMode === 'my_products' && (
        <>
          <div className="border-t border-accent-primary/8 pt-3">
            <h3 className="text-xs font-medium text-neutral-500 uppercase tracking-wider mb-2 px-2">Brand</h3>
            <select
              value={selectedBrand}
              onChange={(e) => { setSelectedBrand(e.target.value); setPage(1); }}
              className="w-full bg-dark-800 border border-accent-primary/12 rounded-lg px-3 py-2 text-sm text-text-secondary focus:outline-none focus:border-accent-primary/30"
            >
              <option value="">All Brands</option>
              {filters?.brands.map(b => (
                <option key={b.name} value={b.name}>{b.name} ({b.count})</option>
              ))}
            </select>
          </div>

          <div className="border-t border-accent-primary/8 pt-3">
            <h3 className="text-xs font-medium text-neutral-500 uppercase tracking-wider mb-2 px-2">Price Range</h3>
            <div className="flex gap-2 px-1">
              <input type="number" placeholder="Min" value={minPrice} onChange={(e) => setMinPrice(e.target.value)}
                className="w-1/2 bg-dark-800 border border-accent-primary/12 rounded-lg px-2.5 py-1.5 text-sm text-text-secondary focus:outline-none focus:border-accent-primary/30" />
              <input type="number" placeholder="Max" value={maxPrice} onChange={(e) => setMaxPrice(e.target.value)}
                className="w-1/2 bg-dark-800 border border-accent-primary/12 rounded-lg px-2.5 py-1.5 text-sm text-text-secondary focus:outline-none focus:border-accent-primary/30" />
            </div>
          </div>

          <div className="border-t border-accent-primary/8 pt-3">
            <h3 className="text-xs font-medium text-neutral-500 uppercase tracking-wider mb-2 px-2">Min Rating</h3>
            <select
              value={minRating}
              onChange={(e) => { setMinRating(e.target.value); setPage(1); }}
              className="w-full bg-dark-800 border border-accent-primary/12 rounded-lg px-3 py-2 text-sm text-text-secondary focus:outline-none focus:border-accent-primary/30"
            >
              <option value="">Any</option>
              <option value="4">4+ Stars</option>
              <option value="3">3+ Stars</option>
              <option value="2">2+ Stars</option>
              <option value="1">1+ Stars</option>
            </select>
          </div>
        </>
      )}

      {(selectedCategory || selectedBrand || minPrice || maxPrice || minRating) && (
        <div className="border-t border-accent-primary/8 pt-3">
          <button
            onClick={() => {
              setSelectedCategory('');
              setSelectedBrand('');
              setMinPrice('');
              setMaxPrice('');
              setMinRating('');
              setExpandedCategories(new Set());
            }}
            className="w-full px-3 py-2 text-sm rounded-lg border border-red-500/20 text-red-600 hover:bg-red-500/10 transition-colors"
          >
            Clear All Filters
          </button>
        </div>
      )}
    </div>
  );
}
