import type { CategoryTreeNode } from '../../services/api';
import type { UseCategoryExplorerReturn } from '../../hooks/useCategoryExplorer';

function CategoryNodeItem({
  node,
  depth,
  selectedCategory,
  expandedCategories,
  toggleCategory,
  selectCategory,
}: {
  node: CategoryTreeNode;
  depth: number;
  selectedCategory: string;
  expandedCategories: Set<string>;
  toggleCategory: (fullPath: string) => void;
  selectCategory: (fullPath: string) => void;
}) {
  const isSelected = selectedCategory === node.full_path;
  const isExpanded = expandedCategories.has(node.full_path);
  const hasChildren = node.children && node.children.length > 0;
  const isAncestor = selectedCategory.startsWith(node.full_path + ' > ');

  return (
    <div key={node.full_path}>
      <div
        className={`flex items-center gap-1 py-1.5 px-2 rounded-md cursor-pointer text-sm transition-colors group ${
          isSelected ? 'bg-accent-primary/10 text-accent-primary' : isAncestor ? 'text-[#7a6b4e] dark:text-[#6B8F80]' : 'text-text-muted hover:text-text-secondary hover:bg-accent-primary/5'
        }`}
        style={{ paddingLeft: `${depth * 14 + 8}px` }}
      >
        {hasChildren && (
          <button
            onClick={(e) => { e.stopPropagation(); toggleCategory(node.full_path); }}
            className="p-0.5 hover:bg-accent-primary/8 rounded flex-shrink-0"
          >
            <svg className={`w-3 h-3 transition-transform ${isExpanded ? 'rotate-90' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
        )}
        {!hasChildren && <span className="w-4" />}
        <span className="flex-1 truncate" onClick={() => selectCategory(node.full_path)}>
          {node.name}
        </span>
        <span className="text-[10px] text-text-faded group-hover:text-neutral-500 flex-shrink-0">{node.count}</span>
      </div>
      {hasChildren && isExpanded && (
        <div>
          {node.children.map(child => (
            <CategoryNodeItem
              key={child.full_path}
              node={child}
              depth={depth + 1}
              selectedCategory={selectedCategory}
              expandedCategories={expandedCategories}
              toggleCategory={toggleCategory}
              selectCategory={selectCategory}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default function CategoryTree({
  categoryTree,
  selectedCategory,
  expandedCategories,
  toggleCategory,
  selectCategory,
}: UseCategoryExplorerReturn) {
  return (
    <div className="max-h-[300px] overflow-y-auto custom-scrollbar">
      {categoryTree.length > 0 ? (
        categoryTree.map(node => (
          <CategoryNodeItem
            key={node.full_path}
            node={node}
            depth={0}
            selectedCategory={selectedCategory}
            expandedCategories={expandedCategories}
            toggleCategory={toggleCategory}
            selectCategory={selectCategory}
          />
        ))
      ) : (
        <p className="text-xs text-text-faded px-2">No categories</p>
      )}
    </div>
  );
}
