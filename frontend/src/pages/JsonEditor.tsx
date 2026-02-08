import { useState, useRef, useCallback, useMemo } from 'react';

interface SubType {
  id: string;
  name: string;
  description: string;
}

interface Metadata {
  group_id: string;
  group_name: string;
  total_products: number;
  description: string;
  sub_types?: SubType[];
  template_fields?: Record<string, string>;
  [key: string]: unknown;
}

interface Product {
  sku: string;
  template: {
    group: string;
    sub_type: string;
    fields: Record<string, unknown>;
  };
  content: {
    short_description: string;
    full_description: string;
    how_to_use: string;
    when_to_use: string;
    target_surface: string;
    why_this_product: string;
  };
  relations: {
    use_before: string[];
    use_after: string[];
    use_with: string[];
    accessories: string[];
    alternatives: string[];
  };
  faq: { question: string; answer: string }[];
  price: number;
  image_url: string;
  category: {
    main_cat: string;
    sub_cat: string;
    sub_cat2: string;
  };
}

interface CategoryData {
  metadata: Metadata;
  products: Product[];
  _fileName: string;
  _originalProducts: string;
}

type SectionKey = 'basic' | 'template' | 'content' | 'relations' | 'faq' | 'metadata';

export default function JsonEditor() {
  const [categories, setCategories] = useState<CategoryData[]>([]);
  const [activeTab, setActiveTab] = useState(0);
  const [activeProduct, setActiveProduct] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const [collapsedSections, setCollapsedSections] = useState<Record<SectionKey, boolean>>({
    basic: false, template: false, content: false, relations: false, faq: false, metadata: true,
  });
  const [relationInputs, setRelationInputs] = useState<Record<string, string>>({});
  const [loadErrors, setLoadErrors] = useState<string[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const currentCategory = categories[activeTab] || null;
  const products = currentCategory?.products || [];

  const filteredProducts = useMemo(() => {
    if (!searchQuery.trim()) return products.map((p, i) => ({ product: p, originalIndex: i }));
    const q = searchQuery.toLowerCase();
    return products
      .map((p, i) => ({ product: p, originalIndex: i }))
      .filter(({ product }) =>
        product.sku.toLowerCase().includes(q) ||
        (product.content?.short_description || '').toLowerCase().includes(q)
      );
  }, [products, searchQuery]);

  const currentProduct = products[activeProduct] || null;

  const hasChanges = useMemo(() => {
    if (!currentCategory) return false;
    return JSON.stringify(currentCategory.products) !== currentCategory._originalProducts;
  }, [currentCategory]);

  const handleFiles = useCallback(async (files: FileList | File[]) => {
    const newCategories: CategoryData[] = [];
    const errors: string[] = [];
    for (const file of Array.from(files)) {
      if (!file.name.endsWith('.json')) {
        errors.push(`${file.name}: Not a .json file`);
        continue;
      }
      try {
        const text = await file.text();
        const data = JSON.parse(text);
        if (data.metadata && data.products) {
          newCategories.push({
            metadata: data.metadata,
            products: data.products,
            _fileName: file.name,
            _originalProducts: JSON.stringify(data.products),
          });
        } else {
          errors.push(`${file.name}: Missing metadata or products`);
        }
      } catch (e) {
        errors.push(`${file.name}: Invalid JSON`);
      }
    }
    if (errors.length > 0) {
      setLoadErrors(errors);
      setTimeout(() => setLoadErrors([]), 5000);
    }
    if (newCategories.length > 0) {
      setCategories(prev => {
        const updated = [...prev, ...newCategories];
        if (prev.length === 0) {
          setActiveTab(0);
          setActiveProduct(0);
        }
        return updated;
      });
    }
  }, []);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    handleFiles(e.dataTransfer.files);
  };

  const toggleSection = (key: SectionKey) => {
    setCollapsedSections(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const ensureProductDefaults = (p: Product): Product => ({
    ...p,
    template: p.template ?? { group: '', sub_type: '', fields: {} },
    content: p.content ?? { short_description: '', full_description: '', how_to_use: '', when_to_use: '', target_surface: '', why_this_product: '' },
    relations: p.relations ?? { use_before: [], use_after: [], use_with: [], accessories: [], alternatives: [] },
    faq: p.faq ?? [],
    category: p.category ?? { main_cat: '', sub_cat: '', sub_cat2: '' },
  });

  const updateProduct = useCallback((updater: (product: Product) => Product) => {
    setCategories(prev => {
      if (activeTab >= prev.length) return prev;
      const updated = [...prev];
      const cat = { ...updated[activeTab] };
      const prods = [...cat.products];
      if (activeProduct >= prods.length) return prev;
      prods[activeProduct] = updater(ensureProductDefaults({ ...prods[activeProduct] }));
      cat.products = prods;
      cat.metadata = { ...cat.metadata, total_products: prods.length };
      updated[activeTab] = cat;
      return updated;
    });
  }, [activeTab, activeProduct]);

  const updateMetadata = useCallback((field: string, value: unknown) => {
    setCategories(prev => {
      const updated = [...prev];
      const cat = { ...updated[activeTab] };
      cat.metadata = { ...cat.metadata, [field]: value };
      updated[activeTab] = cat;
      return updated;
    });
  }, [activeTab]);

  const resetCurrentProduct = () => {
    if (!currentCategory) return;
    try {
      const original = JSON.parse(currentCategory._originalProducts);
      if (original[activeProduct]) {
        setCategories(prev => {
          const updated = [...prev];
          const cat = { ...updated[activeTab] };
          const prods = [...cat.products];
          prods[activeProduct] = original[activeProduct];
          cat.products = prods;
          updated[activeTab] = cat;
          return updated;
        });
      }
    } catch {}
  };

  const downloadCurrent = () => {
    if (!currentCategory) return;
    const { _fileName, _originalProducts, ...rest } = currentCategory;
    const output = { metadata: { ...rest.metadata, total_products: rest.products.length }, products: rest.products };
    const blob = new Blob([JSON.stringify(output, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = _fileName;
    a.click();
    URL.revokeObjectURL(url);
  };

  const downloadAll = () => {
    categories.forEach(cat => {
      const { _fileName, _originalProducts, ...rest } = cat;
      const output = { metadata: { ...rest.metadata, total_products: rest.products.length }, products: rest.products };
      const blob = new Blob([JSON.stringify(output, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = _fileName;
      a.click();
      URL.revokeObjectURL(url);
    });
  };

  const setFieldAtPath = (fields: Record<string, unknown>, fullPath: string[], newValue: unknown): Record<string, unknown> => {
    if (fullPath.length === 0) return fields;
    if (fullPath.length === 1) {
      return { ...fields, [fullPath[0]]: newValue };
    }
    const [head, ...rest] = fullPath;
    const nested = (fields[head] ?? {}) as Record<string, unknown>;
    return { ...fields, [head]: setFieldAtPath({ ...nested }, rest, newValue) };
  };

  const updateFieldValue = (path: string[], key: string, newValue: unknown) => {
    updateProduct(p => {
      const fields = { ...(p.template?.fields ?? {}) };
      const fullPath = [...path, key];
      const updated = setFieldAtPath(fields, fullPath, newValue);
      return { ...p, template: { ...(p.template ?? { group: '', sub_type: '' }), fields: updated } };
    });
  };

  const renderDynamicField = (key: string, value: unknown, path: string[]) => {
    const inputClass = "w-full bg-[#1e1e1e] border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-gray-500 focus:border-[#00d4ff] focus:ring-1 focus:ring-[#00d4ff]/30 transition-colors";

    if (value === null || value === undefined) {
      return (
        <div key={key} className="flex flex-col gap-1">
          <label className="text-xs text-gray-400">{key}</label>
          <input
            className={inputClass}
            value=""
            onChange={(e) => updateFieldValue(path, key, e.target.value)}
            placeholder={`Enter ${key}`}
          />
        </div>
      );
    }

    if (typeof value === 'boolean') {
      return (
        <div key={key} className="flex items-center gap-3 py-1">
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={value}
              onChange={(e) => updateFieldValue(path, key, e.target.checked)}
              className="sr-only peer"
            />
            <div className="w-9 h-5 bg-[#3a3a3a] peer-focus:ring-2 peer-focus:ring-[#00d4ff]/30 rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-gray-400 after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-[#00d4ff]/30 peer-checked:after:bg-[#00d4ff]"></div>
          </label>
          <span className="text-xs text-gray-400">{key}</span>
        </div>
      );
    }

    if (typeof value === 'number') {
      return (
        <div key={key} className="flex flex-col gap-1">
          <label className="text-xs text-gray-400">{key}</label>
          <input
            type="number"
            className={inputClass}
            value={value}
            onChange={(e) => updateFieldValue(path, key, Number(e.target.value) || 0)}
          />
        </div>
      );
    }

    if (Array.isArray(value)) {
      return (
        <div key={key} className="flex flex-col gap-1">
          <label className="text-xs text-gray-400">{key}</label>
          <input
            className={inputClass}
            value={value.join(', ')}
            onChange={(e) => updateFieldValue(path, key, e.target.value.split(',').map(s => s.trim()).filter(Boolean))}
            placeholder="Comma-separated values"
          />
        </div>
      );
    }

    if (typeof value === 'object') {
      return (
        <div key={key} className="flex flex-col gap-2">
          <label className="text-xs text-gray-400 font-medium">{key}</label>
          <div className="pl-3 border-l border-white/10 space-y-2">
            {Object.entries(value as Record<string, unknown>).map(([k, v]) =>
              renderDynamicField(k, v, [...path, key])
            )}
          </div>
        </div>
      );
    }

    return (
      <div key={key} className="flex flex-col gap-1">
        <label className="text-xs text-gray-400">{key}</label>
        <input
          className={inputClass}
          value={String(value)}
          onChange={(e) => updateFieldValue(path, key, e.target.value)}
        />
      </div>
    );
  };

  const renderTagInput = (relationKey: keyof Product['relations']) => {
    const values: string[] = currentProduct?.relations?.[relationKey] || [];
    const inputKey = `${activeTab}-${activeProduct}-${relationKey}`;
    const inputValue = relationInputs[inputKey] || '';

    const addTag = () => {
      const val = inputValue.trim();
      if (!val) return;
      updateProduct(p => {
        const relations = { ...p.relations };
        const arr = [...(relations[relationKey] || [])];
        if (!arr.includes(val)) arr.push(val);
        relations[relationKey] = arr;
        return { ...p, relations };
      });
      setRelationInputs(prev => ({ ...prev, [inputKey]: '' }));
    };

    const removeTag = (idx: number) => {
      updateProduct(p => {
        const relations = { ...p.relations };
        const arr = [...(relations[relationKey] || [])];
        arr.splice(idx, 1);
        relations[relationKey] = arr;
        return { ...p, relations };
      });
    };

    return (
      <div className="flex flex-col gap-2">
        <label className="text-xs text-gray-400 font-medium">{relationKey.replace(/_/g, ' ')}</label>
        <div className="flex flex-wrap gap-1.5 min-h-[36px] bg-[#1e1e1e] border border-white/10 rounded-lg p-2">
          {values.map((v, i) => (
            <span key={i} className="inline-flex items-center gap-1 px-2 py-1 rounded-md bg-[#00d4ff]/10 text-[#00d4ff] text-xs border border-[#00d4ff]/20">
              {v}
              <button onClick={() => removeTag(i)} className="hover:text-red-400 transition-colors ml-0.5">×</button>
            </span>
          ))}
          <input
            className="flex-1 min-w-[120px] bg-transparent text-white text-sm outline-none placeholder-gray-500"
            placeholder="Type SKU & press Enter"
            value={inputValue}
            onChange={(e) => setRelationInputs(prev => ({ ...prev, [inputKey]: e.target.value }))}
            onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addTag(); } }}
          />
        </div>
      </div>
    );
  };

  const SectionHeader = ({ title, sectionKey, icon }: { title: string; sectionKey: SectionKey; icon: React.ReactNode }) => (
    <button
      onClick={() => toggleSection(sectionKey)}
      className="w-full flex items-center justify-between py-3 px-1 group"
    >
      <div className="flex items-center gap-2">
        <span className="text-[#00d4ff]">{icon}</span>
        <span className="text-lg font-semibold text-white">{title}</span>
      </div>
      <svg
        className={`w-5 h-5 text-gray-400 transition-transform duration-200 ${collapsedSections[sectionKey] ? '' : 'rotate-180'}`}
        fill="none" stroke="currentColor" viewBox="0 0 24 24"
      >
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
      </svg>
    </button>
  );

  if (categories.length === 0) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-white mb-2">JSON Product Editor</h1>
          <p className="text-gray-400">Load product catalog JSON files to edit metadata, products, and content.</p>
        </div>

        <div
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={(e) => { e.preventDefault(); setIsDragging(false); }}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-xl p-16 text-center cursor-pointer transition-all duration-200 ${
            isDragging
              ? 'border-[#00d4ff] bg-[#00d4ff]/5'
              : 'border-white/10 hover:border-white/20 bg-[#2a2a2a]'
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".json"
            className="hidden"
            onChange={(e) => e.target.files && handleFiles(e.target.files)}
          />
          <svg className="w-16 h-16 mx-auto mb-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
          <p className="text-lg font-medium text-white mb-2">Drop JSON files here or click to browse</p>
          <p className="text-sm text-gray-500">Accepts multiple .json product catalog files</p>
        </div>

        {loadErrors.length > 0 && (
          <div className="mt-4 bg-red-500/10 border border-red-500/20 rounded-lg p-4">
            <p className="text-sm font-medium text-red-400 mb-1">Some files could not be loaded:</p>
            {loadErrors.map((err, i) => (
              <p key={i} className="text-xs text-red-400/80">{err}</p>
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Top Bar: File upload + Actions */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-bold text-white">JSON Editor</h1>
          {hasChanges && (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-yellow-500/20 text-yellow-400 border border-yellow-500/30">
              <span className="w-1.5 h-1.5 rounded-full bg-yellow-400 animate-pulse" />
              Unsaved Changes
            </span>
          )}
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={() => fileInputRef.current?.click()}
            className="px-3 py-2 bg-white/5 text-gray-300 rounded-lg hover:bg-white/10 border border-white/10 text-sm flex items-center gap-1.5"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Add Files
          </button>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".json"
            className="hidden"
            onChange={(e) => e.target.files && handleFiles(e.target.files)}
          />
          <button
            onClick={resetCurrentProduct}
            className="px-3 py-2 bg-white/5 text-gray-300 rounded-lg hover:bg-white/10 border border-white/10 text-sm"
          >
            Reset Product
          </button>
          <button
            onClick={downloadCurrent}
            className="px-3 py-2 bg-[#00d4ff]/10 text-[#00d4ff] rounded-lg hover:bg-[#00d4ff]/20 border border-[#00d4ff]/20 text-sm font-medium"
          >
            Download Current
          </button>
          <button
            onClick={downloadAll}
            className="px-3 py-2 bg-[#00d4ff] text-[#1e1e1e] rounded-lg font-medium hover:bg-[#00d4ff]/90 text-sm"
          >
            Download All
          </button>
          <button
            onClick={() => { setCategories([]); setActiveTab(0); setActiveProduct(0); }}
            className="px-3 py-2 bg-red-500/10 text-red-400 rounded-lg hover:bg-red-500/20 border border-red-500/20 text-sm"
          >
            Clear All
          </button>
        </div>
      </div>

      {loadErrors.length > 0 && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3 flex items-start gap-2">
          <svg className="w-4 h-4 text-red-400 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
          <div>
            {loadErrors.map((err, i) => (
              <p key={i} className="text-xs text-red-400">{err}</p>
            ))}
          </div>
        </div>
      )}

      {/* Category Tabs */}
      <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-thin">
        {categories.map((cat, i) => (
          <button
            key={i}
            onClick={() => { setActiveTab(i); setActiveProduct(0); setSearchQuery(''); }}
            className={`px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap flex items-center gap-2 transition-all ${
              i === activeTab
                ? 'bg-[#00d4ff]/10 text-[#00d4ff] border border-[#00d4ff]/20'
                : 'bg-white/5 text-gray-400 hover:bg-white/10 hover:text-gray-300 border border-transparent'
            }`}
          >
            {cat.metadata.group_name || cat._fileName}
            <span className={`text-xs px-1.5 py-0.5 rounded-full ${
              i === activeTab ? 'bg-[#00d4ff]/20 text-[#00d4ff]' : 'bg-white/10 text-gray-500'
            }`}>
              {cat.products.length}
            </span>
          </button>
        ))}
      </div>

      {/* Product Navigation */}
      <div className="bg-[#2a2a2a] border border-white/5 rounded-xl p-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
          <div className="flex items-center gap-2 flex-1 min-w-0">
            <button
              onClick={() => setActiveProduct(Math.max(0, activeProduct - 1))}
              disabled={activeProduct === 0}
              className="p-2 rounded-lg bg-white/5 hover:bg-white/10 disabled:opacity-30 disabled:cursor-not-allowed text-gray-300 transition-colors"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>
            <span className="text-sm text-gray-400 tabular-nums min-w-[60px] text-center">
              {products.length > 0 ? `${activeProduct + 1} / ${products.length}` : '0 / 0'}
            </span>
            <button
              onClick={() => setActiveProduct(Math.min(products.length - 1, activeProduct + 1))}
              disabled={activeProduct >= products.length - 1}
              className="p-2 rounded-lg bg-white/5 hover:bg-white/10 disabled:opacity-30 disabled:cursor-not-allowed text-gray-300 transition-colors"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </button>
            <select
              value={activeProduct}
              onChange={(e) => setActiveProduct(Number(e.target.value))}
              className="flex-1 min-w-0 bg-[#1e1e1e] border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:ring-1 focus:ring-[#00d4ff]/30 truncate"
            >
              {products.map((p, i) => (
                <option key={i} value={i}>
                  {p.sku} — {(p.content?.short_description || '').slice(0, 60)}
                </option>
              ))}
            </select>
          </div>
          <div className="relative w-full sm:w-64">
            <svg className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              className="w-full bg-[#1e1e1e] border border-white/10 rounded-lg pl-9 pr-4 py-2 text-white text-sm placeholder-gray-500 focus:border-[#00d4ff] focus:ring-1 focus:ring-[#00d4ff]/30"
              placeholder="Search by SKU or name..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
        </div>
        {searchQuery && (
          <div className="mt-3 max-h-48 overflow-y-auto space-y-1">
            {filteredProducts.length === 0 ? (
              <p className="text-sm text-gray-500 py-2">No products found</p>
            ) : (
              filteredProducts.map(({ product, originalIndex }) => (
                <button
                  key={originalIndex}
                  onClick={() => { setActiveProduct(originalIndex); setSearchQuery(''); }}
                  className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                    originalIndex === activeProduct
                      ? 'bg-[#00d4ff]/10 text-[#00d4ff]'
                      : 'text-gray-300 hover:bg-white/5'
                  }`}
                >
                  <span className="font-mono text-xs text-gray-500 mr-2">{product.sku}</span>
                  {(product.content?.short_description || '').slice(0, 80)}
                </button>
              ))
            )}
          </div>
        )}
      </div>

      {currentProduct && (
        <div className="space-y-4">
          {/* Metadata Panel */}
          <div className="bg-[#2a2a2a] border border-white/5 rounded-xl">
            <div className="px-6 border-b border-white/5">
              <SectionHeader
                title="Metadata"
                sectionKey="metadata"
                icon={
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                }
              />
            </div>
            {!collapsedSections.metadata && currentCategory && (
              <div className="p-6 space-y-4 animate-fade-in">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="flex flex-col gap-1">
                    <label className="text-xs text-gray-400">Group ID</label>
                    <input
                      className="w-full bg-[#1e1e1e] border border-white/10 rounded-lg px-4 py-2.5 text-gray-500 cursor-not-allowed"
                      value={currentCategory.metadata.group_id || ''}
                      readOnly
                    />
                  </div>
                  <div className="flex flex-col gap-1">
                    <label className="text-xs text-gray-400">Group Name</label>
                    <input
                      className="w-full bg-[#1e1e1e] border border-white/10 rounded-lg px-4 py-2.5 text-white focus:border-[#00d4ff] focus:ring-1 focus:ring-[#00d4ff]/30 transition-colors"
                      value={currentCategory.metadata.group_name || ''}
                      onChange={(e) => updateMetadata('group_name', e.target.value)}
                    />
                  </div>
                  <div className="flex flex-col gap-1">
                    <label className="text-xs text-gray-400">Total Products (auto)</label>
                    <input
                      className="w-full bg-[#1e1e1e] border border-white/10 rounded-lg px-4 py-2.5 text-gray-500 cursor-not-allowed"
                      value={currentCategory.products.length}
                      readOnly
                    />
                  </div>
                  <div className="flex flex-col gap-1 md:col-span-2">
                    <label className="text-xs text-gray-400">Description</label>
                    <textarea
                      className="w-full bg-[#1e1e1e] border border-white/10 rounded-lg px-4 py-2.5 text-white focus:border-[#00d4ff] focus:ring-1 focus:ring-[#00d4ff]/30 transition-colors resize-y min-h-[60px]"
                      rows={2}
                      value={currentCategory.metadata.description || ''}
                      onChange={(e) => updateMetadata('description', e.target.value)}
                    />
                  </div>
                </div>

                {currentCategory.metadata.sub_types && currentCategory.metadata.sub_types.length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium text-gray-300 mb-2">Sub Types</h4>
                    <div className="space-y-2">
                      {currentCategory.metadata.sub_types.map((st, i) => (
                        <div key={i} className="flex items-center gap-2 bg-[#1e1e1e] rounded-lg p-2">
                          <input
                            className="w-32 bg-transparent border border-white/10 rounded px-2 py-1 text-xs text-[#00d4ff] font-mono focus:border-[#00d4ff] focus:ring-1 focus:ring-[#00d4ff]/30"
                            value={st.id}
                            onChange={(e) => {
                              const subs = [...(currentCategory.metadata.sub_types || [])];
                              subs[i] = { ...subs[i], id: e.target.value };
                              updateMetadata('sub_types', subs);
                            }}
                          />
                          <input
                            className="flex-1 bg-transparent border border-white/10 rounded px-2 py-1 text-xs text-white focus:border-[#00d4ff] focus:ring-1 focus:ring-[#00d4ff]/30"
                            value={st.name}
                            onChange={(e) => {
                              const subs = [...(currentCategory.metadata.sub_types || [])];
                              subs[i] = { ...subs[i], name: e.target.value };
                              updateMetadata('sub_types', subs);
                            }}
                          />
                          <button
                            onClick={() => {
                              const subs = [...(currentCategory.metadata.sub_types || [])];
                              subs.splice(i, 1);
                              updateMetadata('sub_types', subs);
                            }}
                            className="p-1 text-red-400 hover:text-red-300 transition-colors"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {currentCategory.metadata.template_fields && Object.keys(currentCategory.metadata.template_fields).length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium text-gray-300 mb-2">Template Fields Reference</h4>
                    <div className="bg-[#1e1e1e] rounded-lg p-3 space-y-1">
                      {Object.entries(currentCategory.metadata.template_fields).map(([k, v]) => (
                        <div key={k} className="flex gap-2 text-xs">
                          <span className="text-[#00d4ff] font-mono min-w-[140px]">{k}</span>
                          <span className="text-gray-400">{v}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Basic Info */}
          <div className="bg-[#2a2a2a] border border-white/5 rounded-xl">
            <div className="px-6 border-b border-white/5">
              <SectionHeader
                title="Basic Info"
                sectionKey="basic"
                icon={
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                }
              />
            </div>
            {!collapsedSections.basic && (
              <div className="p-6 space-y-4 animate-fade-in">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  <div className="flex flex-col gap-1">
                    <label className="text-xs text-gray-400">SKU</label>
                    <input
                      className="w-full bg-[#1e1e1e] border border-white/10 rounded-lg px-4 py-2.5 text-gray-500 font-mono cursor-not-allowed"
                      value={currentProduct.sku || ''}
                      readOnly
                    />
                  </div>
                  <div className="flex flex-col gap-1">
                    <label className="text-xs text-gray-400">Price (TL) — stored as kuruş</label>
                    <div className="relative">
                      <input
                        type="number"
                        step="0.01"
                        className="w-full bg-[#1e1e1e] border border-white/10 rounded-lg px-4 py-2.5 text-white focus:border-[#00d4ff] focus:ring-1 focus:ring-[#00d4ff]/30 transition-colors pr-12"
                        value={currentProduct.price != null ? (currentProduct.price / 100).toFixed(2) : ''}
                        onChange={(e) => {
                          const val = parseFloat(e.target.value);
                          updateProduct(p => ({ ...p, price: isNaN(val) ? 0 : Math.round(val * 100) }));
                        }}
                      />
                      <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 text-sm">TL</span>
                    </div>
                  </div>
                  <div className="flex flex-col gap-1">
                    <label className="text-xs text-gray-400">Image URL</label>
                    <input
                      className="w-full bg-[#1e1e1e] border border-white/10 rounded-lg px-4 py-2.5 text-white focus:border-[#00d4ff] focus:ring-1 focus:ring-[#00d4ff]/30 transition-colors"
                      value={currentProduct.image_url || ''}
                      onChange={(e) => updateProduct(p => ({ ...p, image_url: e.target.value }))}
                      placeholder="https://..."
                    />
                  </div>
                </div>
                {currentProduct.image_url && (
                  <div className="flex items-start gap-3">
                    <img
                      src={currentProduct.image_url}
                      alt="Product"
                      className="w-20 h-20 object-cover rounded-lg border border-white/10"
                      onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                    />
                    <span className="text-xs text-gray-500 break-all">{currentProduct.image_url}</span>
                  </div>
                )}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="flex flex-col gap-1">
                    <label className="text-xs text-gray-400">Main Category</label>
                    <input
                      className="w-full bg-[#1e1e1e] border border-white/10 rounded-lg px-4 py-2.5 text-white focus:border-[#00d4ff] focus:ring-1 focus:ring-[#00d4ff]/30 transition-colors"
                      value={currentProduct.category?.main_cat || ''}
                      onChange={(e) => updateProduct(p => ({ ...p, category: { ...p.category, main_cat: e.target.value } }))}
                    />
                  </div>
                  <div className="flex flex-col gap-1">
                    <label className="text-xs text-gray-400">Sub Category</label>
                    <input
                      className="w-full bg-[#1e1e1e] border border-white/10 rounded-lg px-4 py-2.5 text-white focus:border-[#00d4ff] focus:ring-1 focus:ring-[#00d4ff]/30 transition-colors"
                      value={currentProduct.category?.sub_cat || ''}
                      onChange={(e) => updateProduct(p => ({ ...p, category: { ...p.category, sub_cat: e.target.value } }))}
                    />
                  </div>
                  <div className="flex flex-col gap-1">
                    <label className="text-xs text-gray-400">Sub Category 2</label>
                    <input
                      className="w-full bg-[#1e1e1e] border border-white/10 rounded-lg px-4 py-2.5 text-white focus:border-[#00d4ff] focus:ring-1 focus:ring-[#00d4ff]/30 transition-colors"
                      value={currentProduct.category?.sub_cat2 || ''}
                      onChange={(e) => updateProduct(p => ({ ...p, category: { ...p.category, sub_cat2: e.target.value } }))}
                    />
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Template */}
          <div className="bg-[#2a2a2a] border border-white/5 rounded-xl">
            <div className="px-6 border-b border-white/5">
              <SectionHeader
                title="Template"
                sectionKey="template"
                icon={
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z" />
                  </svg>
                }
              />
            </div>
            {!collapsedSections.template && (
              <div className="p-6 space-y-4 animate-fade-in">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="flex flex-col gap-1">
                    <label className="text-xs text-gray-400">Group</label>
                    <input
                      className="w-full bg-[#1e1e1e] border border-white/10 rounded-lg px-4 py-2.5 text-gray-500 cursor-not-allowed"
                      value={currentProduct.template?.group || ''}
                      readOnly
                    />
                  </div>
                  <div className="flex flex-col gap-1">
                    <label className="text-xs text-gray-400">Sub Type</label>
                    <select
                      className="w-full bg-[#1e1e1e] border border-white/10 rounded-lg px-4 py-2.5 text-white focus:border-[#00d4ff] focus:ring-1 focus:ring-[#00d4ff]/30 transition-colors"
                      value={currentProduct.template?.sub_type || ''}
                      onChange={(e) => updateProduct(p => ({
                        ...p,
                        template: { ...p.template, sub_type: e.target.value }
                      }))}
                    >
                      <option value="">— Select —</option>
                      {(currentCategory?.metadata.sub_types || []).map(st => (
                        <option key={st.id} value={st.id}>{st.name} ({st.id})</option>
                      ))}
                    </select>
                  </div>
                </div>

                {currentProduct.template?.fields && Object.keys(currentProduct.template.fields).length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium text-gray-300 mb-3">Dynamic Fields</h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {Object.entries(currentProduct.template.fields).map(([key, value]) =>
                        renderDynamicField(key, value, [])
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Content */}
          <div className="bg-[#2a2a2a] border border-white/5 rounded-xl">
            <div className="px-6 border-b border-white/5">
              <SectionHeader
                title="Content"
                sectionKey="content"
                icon={
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                  </svg>
                }
              />
            </div>
            {!collapsedSections.content && (
              <div className="p-6 space-y-4 animate-fade-in">
                {(['short_description', 'full_description', 'how_to_use', 'when_to_use', 'target_surface', 'why_this_product'] as const).map(field => (
                  <div key={field} className="flex flex-col gap-1">
                    <label className="text-xs text-gray-400">{field.replace(/_/g, ' ')}</label>
                    <textarea
                      className="w-full bg-[#1e1e1e] border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-gray-500 focus:border-[#00d4ff] focus:ring-1 focus:ring-[#00d4ff]/30 transition-colors resize-y"
                      rows={field === 'full_description' ? 10 : field === 'short_description' ? 2 : 4}
                      value={currentProduct.content?.[field] || ''}
                      onChange={(e) => updateProduct(p => ({
                        ...p,
                        content: { ...p.content, [field]: e.target.value }
                      }))}
                      placeholder={`Enter ${field.replace(/_/g, ' ')}...`}
                    />
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Relations */}
          <div className="bg-[#2a2a2a] border border-white/5 rounded-xl">
            <div className="px-6 border-b border-white/5">
              <SectionHeader
                title="Relations"
                sectionKey="relations"
                icon={
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                  </svg>
                }
              />
            </div>
            {!collapsedSections.relations && (
              <div className="p-6 space-y-4 animate-fade-in">
                {renderTagInput('use_before')}
                {renderTagInput('use_after')}
                {renderTagInput('use_with')}
                {renderTagInput('accessories')}
                {renderTagInput('alternatives')}
              </div>
            )}
          </div>

          {/* FAQ */}
          <div className="bg-[#2a2a2a] border border-white/5 rounded-xl">
            <div className="px-6 border-b border-white/5">
              <SectionHeader
                title={`FAQ (${currentProduct.faq?.length || 0})`}
                sectionKey="faq"
                icon={
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                }
              />
            </div>
            {!collapsedSections.faq && (
              <div className="p-6 space-y-4 animate-fade-in">
                {(currentProduct.faq || []).map((item, i) => (
                  <div key={i} className="bg-[#1e1e1e] rounded-lg p-4 border border-white/5 space-y-3">
                    <div className="flex items-start justify-between gap-2">
                      <span className="text-xs text-gray-500 mt-1">Q{i + 1}</span>
                      <button
                        onClick={() => updateProduct(p => {
                          const faq = [...(p.faq || [])];
                          faq.splice(i, 1);
                          return { ...p, faq };
                        })}
                        className="p-1 text-red-400 hover:text-red-300 transition-colors"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                    <div className="flex flex-col gap-1">
                      <label className="text-xs text-gray-400">Question</label>
                      <input
                        className="w-full bg-[#2a2a2a] border border-white/10 rounded-lg px-4 py-2.5 text-white focus:border-[#00d4ff] focus:ring-1 focus:ring-[#00d4ff]/30 transition-colors"
                        value={item.question || ''}
                        onChange={(e) => updateProduct(p => {
                          const faq = [...(p.faq || [])];
                          faq[i] = { ...faq[i], question: e.target.value };
                          return { ...p, faq };
                        })}
                      />
                    </div>
                    <div className="flex flex-col gap-1">
                      <label className="text-xs text-gray-400">Answer</label>
                      <textarea
                        className="w-full bg-[#2a2a2a] border border-white/10 rounded-lg px-4 py-2.5 text-white focus:border-[#00d4ff] focus:ring-1 focus:ring-[#00d4ff]/30 transition-colors resize-y"
                        rows={3}
                        value={item.answer || ''}
                        onChange={(e) => updateProduct(p => {
                          const faq = [...(p.faq || [])];
                          faq[i] = { ...faq[i], answer: e.target.value };
                          return { ...p, faq };
                        })}
                      />
                    </div>
                  </div>
                ))}
                <button
                  onClick={() => updateProduct(p => ({
                    ...p,
                    faq: [...(p.faq || []), { question: '', answer: '' }]
                  }))}
                  className="w-full px-4 py-3 bg-white/5 text-gray-300 rounded-lg hover:bg-white/10 border border-white/10 border-dashed text-sm flex items-center justify-center gap-2 transition-colors"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                  Add FAQ Entry
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
