import { useState, useRef, useCallback, useMemo, useEffect } from 'react';
import axios from 'axios';

const API_BASE = '/api/json-editor';

interface CategoryData {
  metadata: Record<string, unknown>;
  products: Record<string, unknown>[];
  _fileName: string;
  _originalProducts: string;
  _dbId?: string;
}

interface DbFileSummary {
  id: string;
  filename: string;
  product_count: number;
  group_name: string | null;
  created_at: string | null;
  updated_at: string | null;
}

const EMPTY_PRODUCTS: Record<string, unknown>[] = [];

export default function JsonEditor() {
  const [categories, setCategories] = useState<CategoryData[]>([]);
  const [activeTab, setActiveTab] = useState(0);
  const [activeProduct, setActiveProduct] = useState(0);
  const [dbFiles, setDbFiles] = useState<DbFileSummary[]>([]);
  const [loadingFiles, setLoadingFiles] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const [collapsedSections, setCollapsedSections] = useState<Record<string, boolean>>({});
  const [loadErrors, setLoadErrors] = useState<string[]>([]);
  const [addFieldState, setAddFieldState] = useState<Record<string, { key: string; type: string }>>({});
  const [deleteFieldConfirm, setDeleteFieldConfirm] = useState<string | null>(null);
  const [saveToast, setSaveToast] = useState<string | null>(null);
  const [fileListView, setFileListView] = useState(true);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const currentCategory = categories[activeTab] || null;
  const products = currentCategory?.products ?? EMPTY_PRODUCTS;

  const getProductLabel = (p: Record<string, unknown>): string => {
    const sku = String(p.sku || p.SKU || p.id || p.ID || '');
    const desc =
      typeof p.content === 'object' && p.content !== null
        ? String((p.content as Record<string, unknown>).short_description || '')
        : typeof p.name === 'string'
          ? p.name
          : typeof p.title === 'string'
            ? p.title
            : '';
    return sku ? `${sku} — ${desc.slice(0, 60)}` : desc.slice(0, 80) || `Product`;
  };

  const filteredProducts = useMemo(() => {
    if (!searchQuery.trim()) return products.map((p, i) => ({ product: p, originalIndex: i }));
    const q = searchQuery.toLowerCase();
    return products
      .map((p, i) => ({ product: p, originalIndex: i }))
      .filter(({ product }) => getProductLabel(product).toLowerCase().includes(q));
  }, [products, searchQuery]);

  const currentProduct = products[activeProduct] || null;

  const hasChanges = useMemo(() => {
    if (!currentCategory) return false;
    return JSON.stringify(currentCategory.products) !== currentCategory._originalProducts;
  }, [currentCategory]);

  const anyFileHasChanges = useMemo(() => {
    return categories.some(cat => JSON.stringify(cat.products) !== cat._originalProducts);
  }, [categories]);

  const fetchDbFileList = useCallback(async () => {
    try {
      const res = await axios.get(`${API_BASE}/files`);
      setDbFiles(res.data);
    } catch (error) {
      console.error('Failed to fetch JSON files:', error);
    } finally {
      setLoadingFiles(false);
    }
  }, []);

  useEffect(() => {
    fetchDbFileList();
  }, [fetchDbFileList]);

  useEffect(() => {
    const handler = (e: BeforeUnloadEvent) => {
      if (anyFileHasChanges) {
        e.preventDefault();
        e.returnValue = '';
      }
    };
    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, [anyFileHasChanges]);

  const toastTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const showToast = (message: string, duration = 2000) => {
    if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
    setSaveToast(message);
    toastTimerRef.current = setTimeout(() => setSaveToast(null), duration);
  };

  const saveToDb = async () => {
    const cat = currentCategory;
    if (!cat) return;
    try {
      const content = { metadata: cat.metadata, products: cat.products };
      if (cat._dbId) {
        await axios.put(`${API_BASE}/files/${cat._dbId}`, { content });
      } else {
        const res = await axios.post(`${API_BASE}/files`, { filename: cat._fileName, content });
        setCategories(prev => prev.map((c, i) => i === activeTab ? { ...c, _dbId: res.data.id } : c));
      }
      setCategories(prev => prev.map((c, i) => i === activeTab ? { ...c, _originalProducts: JSON.stringify(c.products) } : c));
      showToast('Saved to database!');
      fetchDbFileList();
    } catch {
      showToast('Save failed', 3000);
    }
  };

  useEffect(() => {
    return () => {
      if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
    };
  }, []);

  const clearAllFiles = async () => {
    try {
      await axios.delete(`${API_BASE}/files`);
      setCategories([]);
      setActiveTab(0);
      setActiveProduct(0);
      setDbFiles([]);
    } catch (error) {
      console.error('Failed to clear JSON files:', error);
      showToast('Failed to clear files', 3000);
    }
  };

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
          const content = { metadata: data.metadata, products: data.products };
          const res = await axios.post(`${API_BASE}/files`, { filename: file.name, content });
          newCategories.push({
            metadata: data.metadata,
            products: data.products,
            _fileName: file.name,
            _originalProducts: JSON.stringify(data.products),
            _dbId: res.data.id,
          });
        } else {
          errors.push(`${file.name}: Missing metadata or products`);
        }
      } catch {
        errors.push(`${file.name}: Invalid JSON or upload failed`);
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
      fetchDbFileList();
    }
  }, [fetchDbFileList]);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    handleFiles(e.dataTransfer.files);
  };

  const toggleSection = (key: string) => {
    setCollapsedSections(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const updateProduct = useCallback((updater: (product: Record<string, unknown>) => Record<string, unknown>) => {
    setCategories(prev => {
      if (activeTab >= prev.length) return prev;
      const updated = [...prev];
      const cat = { ...updated[activeTab] };
      const prods = [...cat.products];
      if (activeProduct >= prods.length) return prev;
      prods[activeProduct] = updater({ ...prods[activeProduct] });
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

  const setValueAtPath = (obj: unknown, path: string[], value: unknown): unknown => {
    if (path.length === 0) return value;
    const [head, ...rest] = path;
    if (Array.isArray(obj)) {
      const idx = parseInt(head, 10);
      const arr = [...obj];
      arr[idx] = setValueAtPath(arr[idx], rest, value);
      return arr;
    }
    const record = (obj ?? {}) as Record<string, unknown>;
    return { ...record, [head]: setValueAtPath(record[head], rest, value) };
  };

  const deleteKeyAtPath = (obj: unknown, path: string[]): unknown => {
    if (path.length === 0) return obj;
    const [head, ...rest] = path;
    if (Array.isArray(obj)) {
      const idx = parseInt(head, 10);
      if (rest.length === 0) {
        const arr = [...obj];
        arr.splice(idx, 1);
        return arr;
      }
      const arr = [...obj];
      arr[idx] = deleteKeyAtPath(arr[idx], rest);
      return arr;
    }
    const record = (obj ?? {}) as Record<string, unknown>;
    if (rest.length === 0) {
      const copy = { ...record };
      delete copy[head];
      return copy;
    }
    return { ...record, [head]: deleteKeyAtPath(record[head], rest) };
  };

  const updateAtPath = (path: string[], value: unknown) => {
    updateProduct(p => setValueAtPath(p, path, value) as Record<string, unknown>);
  };

  const deleteAtPath = (path: string[]) => {
    updateProduct(p => deleteKeyAtPath(p, path) as Record<string, unknown>);
    setDeleteFieldConfirm(null);
  };

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
    } catch (error) {
      console.error('Failed to reset current product:', error);
      showToast('Failed to reset current product', 3000);
    }
  };

  const downloadCurrent = () => {
    if (!currentCategory) return;
    const output = {
      metadata: { ...currentCategory.metadata, total_products: currentCategory.products.length },
      products: currentCategory.products
    };
    const blob = new Blob([JSON.stringify(output, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = currentCategory._fileName;
    a.click();
    URL.revokeObjectURL(url);
  };

  const downloadAll = () => {
    categories.forEach(cat => {
      const output = {
        metadata: { ...cat.metadata, total_products: cat.products.length },
        products: cat.products
      };
      const blob = new Blob([JSON.stringify(output, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = cat._fileName;
      a.click();
      URL.revokeObjectURL(url);
    });
  };

  const isLongString = (val: unknown): boolean => typeof val === 'string' && val.length > 100;
  const isFaqArray = (val: unknown): boolean =>
    Array.isArray(val) && val.length > 0 && typeof val[0] === 'object' && val[0] !== null && 'question' in val[0] && 'answer' in val[0];
  const isStringArray = (val: unknown): boolean =>
    Array.isArray(val) && (val.length === 0 || typeof val[0] === 'string');
  const isObjectArray = (val: unknown): boolean =>
    Array.isArray(val) && val.length > 0 && typeof val[0] === 'object' && val[0] !== null;

  const inputClass = "w-full bg-[#f7eede] border border-[#5b4824]/12 rounded-lg px-4 py-2.5 text-[#0f1419] placeholder-neutral-500 focus:border-accent-primary focus:ring-1 focus:ring-accent-primary/30 transition-colors";

  const AddFieldButton = ({ path, target }: { path: string[]; target: 'product' | 'metadata' }) => {
    const stateKey = path.join('.');
    const state = addFieldState[stateKey];

    if (!state) {
      return (
        <button
          onClick={() => setAddFieldState(prev => ({ ...prev, [stateKey]: { key: '', type: 'string' } }))}
          className="w-full px-4 py-2.5 bg-[#5b4824]/5 text-[#9e8b66] rounded-lg hover:bg-[#5b4824]/8 border border-[#5b4824]/12 border-dashed text-sm flex items-center justify-center gap-2 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Add Field
        </button>
      );
    }

    const addField = () => {
      const key = state.key.trim();
      if (!key) return;
      let defaultValue: unknown;
      switch (state.type) {
        case 'string': defaultValue = ''; break;
        case 'number': defaultValue = 0; break;
        case 'boolean': defaultValue = false; break;
        case 'array': defaultValue = []; break;
        case 'object': defaultValue = {}; break;
        case 'textarea': defaultValue = ''; break;
        default: defaultValue = '';
      }
      if (target === 'metadata') {
        const metaPath = path.length > 0 ? [...path.slice(1), key] : [key];
        if (metaPath.length === 1) {
          updateMetadata(metaPath[0], defaultValue);
        } else {
          const topKey = metaPath[0];
          const subPath = metaPath.slice(1);
          const current = (currentCategory?.metadata || {})[topKey] || {};
          const updated = setValueAtPath(current, subPath, defaultValue);
          updateMetadata(topKey, updated);
        }
      } else {
        updateAtPath([...path, key], defaultValue);
      }
      setAddFieldState(prev => {
        const copy = { ...prev };
        delete copy[stateKey];
        return copy;
      });
    };

    return (
      <div className="flex flex-wrap items-center gap-2 bg-[#f7eede] rounded-lg p-3 border border-accent-primary/20">
        <input
          className="flex-1 min-w-[120px] bg-[#fefbf0] border border-[#5b4824]/12 rounded-lg px-3 py-2 text-[#0f1419] text-sm placeholder-neutral-500 focus:border-accent-primary focus:ring-1 focus:ring-accent-primary/30"
          placeholder="Field name"
          value={state.key}
          onChange={(e) => setAddFieldState(prev => ({ ...prev, [stateKey]: { ...prev[stateKey], key: e.target.value } }))}
          onKeyDown={(e) => { if (e.key === 'Enter') addField(); }}
          autoFocus
        />
        <select
          className="bg-[#fefbf0] border border-[#5b4824]/12 rounded-lg px-3 py-2 text-[#0f1419] text-sm focus:border-accent-primary"
          value={state.type}
          onChange={(e) => setAddFieldState(prev => ({ ...prev, [stateKey]: { ...prev[stateKey], type: e.target.value } }))}
        >
          <option value="string">Text</option>
          <option value="textarea">Long Text</option>
          <option value="number">Number</option>
          <option value="boolean">Boolean</option>
          <option value="array">Array</option>
          <option value="object">Object</option>
        </select>
        <button
          onClick={addField}
          disabled={!state.key.trim()}
          className="px-3 py-2 bg-accent-primary/10 text-accent-primary rounded-lg hover:bg-accent-primary/20 border border-accent-primary/20 text-sm font-medium disabled:opacity-30"
        >
          Add
        </button>
        <button
          onClick={() => setAddFieldState(prev => {
            const copy = { ...prev };
            delete copy[stateKey];
            return copy;
          })}
          className="p-2 text-[#9e8b66] hover:text-[#5f471d]"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    );
  };

  const DeleteFieldButton = ({ path }: { path: string[] }) => {
    const pathKey = path.join('.');
    if (deleteFieldConfirm === pathKey) {
      return (
        <div className="flex items-center gap-1">
          <button
            onClick={() => deleteAtPath(path)}
            className="px-2 py-1 bg-red-500/20 text-red-400 rounded text-xs hover:bg-red-500/30 border border-red-500/30"
          >
            Confirm
          </button>
          <button
            onClick={() => setDeleteFieldConfirm(null)}
            className="px-2 py-1 text-[#9e8b66] rounded text-xs hover:text-[#5f471d]"
          >
            Cancel
          </button>
        </div>
      );
    }
    return (
      <button
        onClick={() => setDeleteFieldConfirm(pathKey)}
        className="p-1 text-[#b5a382] hover:text-red-400 transition-colors opacity-100 md:opacity-0 md:group-hover:opacity-100"
        title="Delete field"
      >
        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
        </svg>
      </button>
    );
  };

  const renderValue = (key: string, value: unknown, path: string[], showDelete = true): React.ReactNode => {
    const fullPath = [...path, key];

    if (value === null || value === undefined) {
      return (
        <div key={key} className="flex flex-col gap-1 group">
          <div className="flex items-center gap-2">
            <label className="text-xs text-[#9e8b66]">{key}</label>
            {showDelete && <DeleteFieldButton path={fullPath} />}
          </div>
          <input
            className={inputClass}
            value=""
            onChange={(e) => updateAtPath(fullPath, e.target.value)}
            placeholder={`Enter ${key}`}
          />
        </div>
      );
    }

    if (typeof value === 'boolean') {
      return (
        <div key={key} className="flex items-center gap-3 py-1 group">
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={value}
              onChange={(e) => updateAtPath(fullPath, e.target.checked)}
              className="sr-only peer"
            />
            <div className="w-9 h-5 bg-[#f0e8d8] peer-focus:ring-2 peer-focus:ring-accent-primary/30 rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-gray-400 after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-accent-primary/30 peer-checked:after:bg-accent-primary"></div>
          </label>
          <span className="text-xs text-[#9e8b66]">{key}</span>
          {showDelete && <DeleteFieldButton path={fullPath} />}
        </div>
      );
    }

    if (typeof value === 'number') {
      return (
        <div key={key} className="flex flex-col gap-1 group">
          <div className="flex items-center gap-2">
            <label className="text-xs text-[#9e8b66]">{key}</label>
            {showDelete && <DeleteFieldButton path={fullPath} />}
          </div>
          <input
            type="number"
            className={inputClass}
            value={value}
            onChange={(e) => updateAtPath(fullPath, Number(e.target.value) || 0)}
          />
        </div>
      );
    }

    if (isFaqArray(value)) {
      const items = value as { question: string; answer: string }[];
      return (
        <div key={key} className="flex flex-col gap-3">
          <div className="flex items-center gap-2 group">
            <label className="text-xs text-[#9e8b66] font-medium">{key} ({items.length})</label>
            {showDelete && <DeleteFieldButton path={fullPath} />}
          </div>
          {items.map((item, i) => (
            <div key={i} className="bg-[#f7eede] rounded-lg p-4 border border-[#5b4824]/8 space-y-3">
              <div className="flex items-start justify-between gap-2">
                <span className="text-xs text-neutral-500">Q{i + 1}</span>
                <button
                  onClick={() => {
                    const arr = [...items];
                    arr.splice(i, 1);
                    updateAtPath(fullPath, arr);
                  }}
                  className="p-1 text-red-400 hover:text-red-300 transition-colors"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs text-[#9e8b66]">Question</label>
                <input
                  className="w-full bg-[#fefbf0] border border-[#5b4824]/12 rounded-lg px-4 py-2.5 text-[#0f1419] focus:border-accent-primary focus:ring-1 focus:ring-accent-primary/30 transition-colors"
                  value={item.question || ''}
                  onChange={(e) => {
                    const arr = [...items];
                    arr[i] = { ...arr[i], question: e.target.value };
                    updateAtPath(fullPath, arr);
                  }}
                />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs text-[#9e8b66]">Answer</label>
                <textarea
                  className="w-full bg-[#fefbf0] border border-[#5b4824]/12 rounded-lg px-4 py-2.5 text-[#0f1419] focus:border-accent-primary focus:ring-1 focus:ring-accent-primary/30 transition-colors resize-y"
                  rows={3}
                  value={item.answer || ''}
                  onChange={(e) => {
                    const arr = [...items];
                    arr[i] = { ...arr[i], answer: e.target.value };
                    updateAtPath(fullPath, arr);
                  }}
                />
              </div>
            </div>
          ))}
          <button
            onClick={() => updateAtPath(fullPath, [...items, { question: '', answer: '' }])}
            className="w-full px-4 py-3 bg-[#5b4824]/5 text-[#5f471d] rounded-lg hover:bg-[#5b4824]/8 border border-[#5b4824]/12 border-dashed text-sm flex items-center justify-center gap-2 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Add Entry
          </button>
        </div>
      );
    }

    if (isStringArray(value)) {
      const items = value as string[];
      return (
        <div key={key} className="flex flex-col gap-2 group">
          <div className="flex items-center gap-2">
            <label className="text-xs text-[#9e8b66] font-medium">{key.replace(/_/g, ' ')}</label>
            {showDelete && <DeleteFieldButton path={fullPath} />}
          </div>
          <TagInput values={items} onChange={(v) => updateAtPath(fullPath, v)} />
        </div>
      );
    }

    if (isObjectArray(value)) {
      const items = value as Record<string, unknown>[];
      return (
        <div key={key} className="flex flex-col gap-3">
          <div className="flex items-center gap-2 group">
            <label className="text-xs text-[#9e8b66] font-medium">{key} ({items.length})</label>
            {showDelete && <DeleteFieldButton path={fullPath} />}
          </div>
          {items.map((item, i) => (
            <div key={i} className="bg-[#f7eede] rounded-lg p-4 border border-[#5b4824]/8 space-y-3">
              <div className="flex items-start justify-between gap-2">
                <span className="text-xs text-neutral-500">#{i + 1}</span>
                <button
                  onClick={() => {
                    const arr = [...items];
                    arr.splice(i, 1);
                    updateAtPath(fullPath, arr);
                  }}
                  className="p-1 text-red-400 hover:text-red-300 transition-colors"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              {Object.entries(item).map(([k, v]) => renderValue(k, v, [...fullPath, String(i)], true))}
            </div>
          ))}
          <button
            onClick={() => {
              const template = items.length > 0
                ? Object.fromEntries(Object.keys(items[0]).map(k => [k, '']))
                : {};
              updateAtPath(fullPath, [...items, template]);
            }}
            className="w-full px-4 py-3 bg-[#5b4824]/5 text-[#5f471d] rounded-lg hover:bg-[#5b4824]/8 border border-[#5b4824]/12 border-dashed text-sm flex items-center justify-center gap-2 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Add Entry
          </button>
        </div>
      );
    }

    if (Array.isArray(value)) {
      return (
        <div key={key} className="flex flex-col gap-1 group">
          <div className="flex items-center gap-2">
            <label className="text-xs text-[#9e8b66]">{key}</label>
            {showDelete && <DeleteFieldButton path={fullPath} />}
          </div>
          <textarea
            className={inputClass + " resize-y"}
            rows={3}
            value={JSON.stringify(value, null, 2)}
            onChange={(e) => {
              try {
                updateAtPath(fullPath, JSON.parse(e.target.value));
              } catch {
                return;
              }
            }}
          />
        </div>
      );
    }

    if (typeof value === 'object' && value !== null) {
      const entries = Object.entries(value as Record<string, unknown>);
      return (
        <div key={key} className="flex flex-col gap-2">
          <div className="flex items-center gap-2 group">
            <label className="text-xs text-[#9e8b66] font-medium">{key}</label>
            <span className="text-xs text-[#b5a382]">({entries.length} fields)</span>
            {showDelete && <DeleteFieldButton path={fullPath} />}
          </div>
          <div className="pl-3 border-l-2 border-[#5b4824]/8 space-y-3">
            {entries.map(([k, v]) => renderValue(k, v, fullPath, true))}
            <AddFieldButton path={fullPath} target="product" />
          </div>
        </div>
      );
    }

    if (isLongString(value)) {
      return (
        <div key={key} className="flex flex-col gap-1 group">
          <div className="flex items-center gap-2">
            <label className="text-xs text-[#9e8b66]">{key.replace(/_/g, ' ')}</label>
            {showDelete && <DeleteFieldButton path={fullPath} />}
          </div>
          <textarea
            className={inputClass + " resize-y"}
            rows={Math.min(12, Math.max(3, Math.ceil(String(value).length / 120)))}
            value={String(value)}
            onChange={(e) => updateAtPath(fullPath, e.target.value)}
          />
        </div>
      );
    }

    return (
      <div key={key} className="flex flex-col gap-1 group">
        <div className="flex items-center gap-2">
          <label className="text-xs text-[#9e8b66]">{key.replace(/_/g, ' ')}</label>
          {showDelete && <DeleteFieldButton path={fullPath} />}
        </div>
        <input
          className={inputClass}
          value={String(value)}
          onChange={(e) => updateAtPath(fullPath, e.target.value)}
        />
      </div>
    );
  };

  const TagInput = ({ values, onChange }: { values: string[]; onChange: (v: string[]) => void }) => {
    const [inputVal, setInputVal] = useState('');
    return (
      <div className="flex flex-wrap gap-1.5 min-h-[36px] bg-[#f7eede] border border-[#5b4824]/12 rounded-lg p-2">
        {values.map((v, i) => (
          <span key={i} className="inline-flex items-center gap-1 px-2 py-1 rounded-md bg-accent-primary/10 text-accent-primary text-xs border border-accent-primary/20">
            {v}
            <button onClick={() => onChange(values.filter((_, idx) => idx !== i))} className="hover:text-red-400 transition-colors ml-0.5">×</button>
          </span>
        ))}
        <input
          className="flex-1 min-w-[120px] bg-transparent text-[#0f1419] text-sm outline-none placeholder-neutral-500"
          placeholder="Type & press Enter"
          value={inputVal}
          onChange={(e) => setInputVal(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault();
              const val = inputVal.trim();
              if (val && !values.includes(val)) {
                onChange([...values, val]);
                setInputVal('');
              }
            }
          }}
        />
      </div>
    );
  };

  const sectionIcons: Record<string, React.ReactNode> = {
    template: <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z" /></svg>,
    content: <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" /></svg>,
    relations: <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" /></svg>,
    faq: <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>,
    category: <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" /></svg>,
    cleaned_content: <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>,
  };

  const defaultIcon = <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 6h16M4 12h16M4 18h7" /></svg>;

  const primitiveKeys = useMemo(() => {
    if (!currentProduct) return [];
    return Object.keys(currentProduct).filter(k => {
      const v = currentProduct[k];
      return typeof v !== 'object' || v === null;
    });
  }, [currentProduct]);

  const objectKeys = useMemo(() => {
    if (!currentProduct) return [];
    return Object.keys(currentProduct).filter(k => {
      const v = currentProduct[k];
      return v !== null && typeof v === 'object';
    });
  }, [currentProduct]);

  const renderPrimitiveFields = () => {
    if (!currentProduct || primitiveKeys.length === 0) return null;

    const priceKey = primitiveKeys.find(k => k === 'price');
    const imageKey = primitiveKeys.find(k => k === 'image_url' || k === 'imageUrl' || k === 'image');
    const skuKey = primitiveKeys.find(k => k === 'sku' || k === 'SKU' || k === 'id');
    const otherKeys = primitiveKeys.filter(k => k !== priceKey && k !== imageKey && k !== skuKey);

    return (
      <div className="bg-[#fefbf0] border border-[#5b4824]/8 rounded-xl">
        <button
          onClick={() => toggleSection('_basic')}
          className="w-full flex items-center justify-between py-3 px-4 md:px-6 border-b border-[#5b4824]/8"
        >
          <div className="flex items-center gap-2">
            <span className="text-accent-primary">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </span>
            <span className="text-base md:text-lg font-semibold text-[#0f1419]">Basic Info</span>
            <span className="text-xs text-neutral-500">({primitiveKeys.length})</span>
          </div>
          <svg className={`w-5 h-5 text-[#9e8b66] transition-transform duration-200 ${collapsedSections['_basic'] ? '' : 'rotate-180'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>
        {!collapsedSections['_basic'] && (
          <div className="p-4 md:p-6 space-y-4 animate-fade-in">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 md:gap-4">
              {skuKey && (
                <div className="flex flex-col gap-1">
                  <label className="text-xs text-[#9e8b66]">{skuKey}</label>
                  <input className={inputClass + " !text-neutral-500 cursor-not-allowed"} value={String(currentProduct[skuKey] || '')} readOnly />
                </div>
              )}
              {priceKey && (
                <div className="flex flex-col gap-1">
                  <label className="text-xs text-[#9e8b66]">Price (TL) — stored as kuruş</label>
                  <div className="relative">
                    <input
                      type="number"
                      step="0.01"
                      className={inputClass + " pr-12"}
                      value={currentProduct[priceKey] != null ? (Number(currentProduct[priceKey]) / 100).toFixed(2) : ''}
                      onChange={(e) => {
                        const val = parseFloat(e.target.value);
                        updateAtPath([priceKey], isNaN(val) ? 0 : Math.round(val * 100));
                      }}
                    />
                    <span className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-500 text-sm">TL</span>
                  </div>
                </div>
              )}
              {imageKey && (
                <div className="flex flex-col gap-1">
                  <label className="text-xs text-[#9e8b66]">{imageKey}</label>
                  <input
                    className={inputClass}
                    value={String(currentProduct[imageKey] || '')}
                    onChange={(e) => updateAtPath([imageKey], e.target.value)}
                    placeholder="https://..."
                  />
                </div>
              )}
            </div>
            {imageKey && typeof currentProduct[imageKey] === 'string' && currentProduct[imageKey] && (
              <div className="flex items-start gap-3">
                <img
                  src={String(currentProduct[imageKey])}
                  alt="Product"
                  className="w-20 h-20 object-cover rounded-lg border border-[#5b4824]/12"
                  onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                />
                <span className="text-xs text-neutral-500 break-all">{String(currentProduct[imageKey])}</span>
              </div>
            )}
            {otherKeys.length > 0 && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 md:gap-4">
                {otherKeys.map(key => renderValue(key, currentProduct[key], [], true))}
              </div>
            )}
            <AddFieldButton path={[]} target="product" />
          </div>
        )}
      </div>
    );
  };

  const renderObjectSection = (key: string) => {
    if (!currentProduct) return null;
    const value = currentProduct[key];
    if (value === null || typeof value !== 'object') return null;

    const sectionId = `_sec_${key}`;
    const isCollapsed = collapsedSections[sectionId];
    const icon = sectionIcons[key] || defaultIcon;
    const displayName = key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

    if (isFaqArray(value)) {
      return (
        <div key={key} className="bg-[#fefbf0] border border-[#5b4824]/8 rounded-xl">
          <button onClick={() => toggleSection(sectionId)} className="w-full flex items-center justify-between py-3 px-4 md:px-6 border-b border-[#5b4824]/8">
            <div className="flex items-center gap-2 min-w-0">
              <span className="text-accent-primary shrink-0">{icon}</span>
              <span className="text-base md:text-lg font-semibold text-[#0f1419] truncate">{displayName}</span>
              <span className="text-xs text-neutral-500 shrink-0">({(value as unknown[]).length})</span>
            </div>
            <svg className={`w-5 h-5 text-[#9e8b66] transition-transform duration-200 shrink-0 ${isCollapsed ? '' : 'rotate-180'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          {!isCollapsed && (
            <div className="p-4 md:p-6 animate-fade-in">
              {renderValue(key, value, [], false)}
            </div>
          )}
        </div>
      );
    }

    if (Array.isArray(value)) {
      return (
        <div key={key} className="bg-[#fefbf0] border border-[#5b4824]/8 rounded-xl">
          <button onClick={() => toggleSection(sectionId)} className="w-full flex items-center justify-between py-3 px-4 md:px-6 border-b border-[#5b4824]/8">
            <div className="flex items-center gap-2 min-w-0">
              <span className="text-accent-primary shrink-0">{icon}</span>
              <span className="text-base md:text-lg font-semibold text-[#0f1419] truncate">{displayName}</span>
              <span className="text-xs text-neutral-500 shrink-0">({value.length})</span>
            </div>
            <svg className={`w-5 h-5 text-[#9e8b66] transition-transform duration-200 shrink-0 ${isCollapsed ? '' : 'rotate-180'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          {!isCollapsed && (
            <div className="p-4 md:p-6 animate-fade-in">
              {renderValue(key, value, [], false)}
            </div>
          )}
        </div>
      );
    }

    const entries = Object.entries(value as Record<string, unknown>);
    return (
      <div key={key} className="bg-[#fefbf0] border border-[#5b4824]/8 rounded-xl">
        <button onClick={() => toggleSection(sectionId)} className="w-full flex items-center justify-between py-3 px-4 md:px-6 border-b border-[#5b4824]/8">
          <div className="flex items-center gap-2 min-w-0">
            <span className="text-accent-primary shrink-0">{icon}</span>
            <span className="text-base md:text-lg font-semibold text-[#0f1419] truncate">{displayName}</span>
            <span className="text-xs text-neutral-500 shrink-0">({entries.length})</span>
          </div>
          <svg className={`w-5 h-5 text-[#9e8b66] transition-transform duration-200 shrink-0 ${isCollapsed ? '' : 'rotate-180'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>
        {!isCollapsed && (
          <div className="p-4 md:p-6 space-y-4 animate-fade-in">
            {key === 'template' ? (
              <>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {entries.filter(([k]) => k !== 'fields').map(([k, v]) => {
                    if (k === 'sub_type' && currentCategory?.metadata) {
                      const subTypes = currentCategory.metadata.sub_types as { id: string; name: string }[] | undefined;
                      if (subTypes && subTypes.length > 0) {
                        return (
                          <div key={k} className="flex flex-col gap-1">
                            <label className="text-xs text-[#9e8b66]">Sub Type</label>
                            <select
                              className={inputClass}
                              value={String(v || '')}
                              onChange={(e) => updateAtPath([key, k], e.target.value)}
                            >
                              <option value="">— Select —</option>
                              {subTypes.map(st => (
                                <option key={st.id} value={st.id}>{st.name} ({st.id})</option>
                              ))}
                            </select>
                          </div>
                        );
                      }
                    }
                    return renderValue(k, v, [key], true);
                  })}
                </div>
                {(value as Record<string, unknown>).fields && (
                  <div>
                    <h4 className="text-sm font-medium text-[#5f471d] mb-3">Dynamic Fields</h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {Object.entries((value as Record<string, unknown>).fields as Record<string, unknown>).map(([k, v]) =>
                        renderValue(k, v, [key, 'fields'], true)
                      )}
                    </div>
                    <div className="mt-3">
                      <AddFieldButton path={[key, 'fields']} target="product" />
                    </div>
                  </div>
                )}
                {!(value as Record<string, unknown>).fields && (
                  <AddFieldButton path={[key]} target="product" />
                )}
              </>
            ) : (
              <>
                <div className="space-y-4">
                  {entries.map(([k, v]) => renderValue(k, v, [key], true))}
                </div>
                <AddFieldButton path={[key]} target="product" />
              </>
            )}
          </div>
        )}
      </div>
    );
  };

  const renderMetadataSection = () => {
    if (!currentCategory) return null;
    const meta = currentCategory.metadata;
    const metaEntries = Object.entries(meta);

    return (
      <div className="bg-[#fefbf0] border border-[#5b4824]/8 rounded-xl">
        <button onClick={() => toggleSection('_metadata')} className="w-full flex items-center justify-between py-3 px-4 md:px-6 border-b border-[#5b4824]/8">
          <div className="flex items-center gap-2">
            <span className="text-accent-primary">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </span>
            <span className="text-base md:text-lg font-semibold text-[#0f1419]">Metadata</span>
            <span className="text-xs text-neutral-500">({metaEntries.length})</span>
          </div>
          <svg className={`w-5 h-5 text-[#9e8b66] transition-transform duration-200 ${collapsedSections['_metadata'] ? '' : 'rotate-180'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>
        {!collapsedSections['_metadata'] && (
          <div className="p-4 md:p-6 space-y-4 animate-fade-in">
            {metaEntries.map(([key, value]) => {
              if (key === 'total_products') {
                return (
                  <div key={key} className="flex flex-col gap-1">
                    <label className="text-xs text-[#9e8b66]">total_products (auto)</label>
                    <input className={inputClass + " !text-neutral-500 cursor-not-allowed"} value={String(currentCategory.products.length)} readOnly />
                  </div>
                );
              }
              if (key === 'sub_types' && Array.isArray(value)) {
                const subTypes = value as { id: string; name: string; description?: string }[];
                return (
                  <div key={key}>
                    <h4 className="text-sm font-medium text-[#5f471d] mb-2">Sub Types ({subTypes.length})</h4>
                    <div className="space-y-2">
                      {subTypes.map((st, i) => (
                        <div key={i} className="flex flex-wrap items-center gap-2 bg-[#f7eede] rounded-lg p-2">
                          <input
                            className="w-full sm:w-32 bg-transparent border border-[#5b4824]/12 rounded px-2 py-1 text-xs text-accent-primary font-mono focus:border-accent-primary focus:ring-1 focus:ring-accent-primary/30"
                            value={st.id || ''}
                            onChange={(e) => {
                              const subs = [...subTypes];
                              subs[i] = { ...subs[i], id: e.target.value };
                              updateMetadata('sub_types', subs);
                            }}
                          />
                          <input
                            className="flex-1 bg-transparent border border-[#5b4824]/12 rounded px-2 py-1 text-xs text-[#0f1419] focus:border-accent-primary focus:ring-1 focus:ring-accent-primary/30"
                            value={st.name || ''}
                            onChange={(e) => {
                              const subs = [...subTypes];
                              subs[i] = { ...subs[i], name: e.target.value };
                              updateMetadata('sub_types', subs);
                            }}
                          />
                          <button
                            onClick={() => {
                              const subs = [...subTypes];
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
                      <button
                        onClick={() => updateMetadata('sub_types', [...subTypes, { id: '', name: '', description: '' }])}
                        className="w-full px-4 py-2 bg-[#5b4824]/5 text-[#5f471d] rounded-lg hover:bg-[#5b4824]/8 border border-[#5b4824]/12 border-dashed text-sm flex items-center justify-center gap-2 transition-colors"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                        </svg>
                        Add Sub Type
                      </button>
                    </div>
                  </div>
                );
              }
              if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
                return (
                  <div key={key} className="flex flex-col gap-2">
                    <label className="text-xs text-[#9e8b66] font-medium">{key}</label>
                    <div className="bg-[#f7eede] rounded-lg p-3 space-y-2">
                      {Object.entries(value as Record<string, unknown>).map(([k, v]) => (
                        <div key={k} className="flex flex-col gap-1">
                          <label className="text-xs text-neutral-500">{k}</label>
                          <input
                            className={inputClass}
                            value={String(v || '')}
                            onChange={(e) => {
                              const updated = { ...(meta[key] as Record<string, unknown>), [k]: e.target.value };
                              updateMetadata(key, updated);
                            }}
                          />
                        </div>
                      ))}
                    </div>
                  </div>
                );
              }
              if (typeof value === 'string' && value.length > 100) {
                return (
                  <div key={key} className="flex flex-col gap-1">
                    <label className="text-xs text-[#9e8b66]">{key}</label>
                    <textarea
                      className={inputClass + " resize-y"}
                      rows={3}
                      value={value}
                      onChange={(e) => updateMetadata(key, e.target.value)}
                    />
                  </div>
                );
              }
              if (typeof value === 'number') {
                return (
                  <div key={key} className="flex flex-col gap-1">
                    <label className="text-xs text-[#9e8b66]">{key}</label>
                    <input
                      type="number"
                      className={inputClass}
                      value={value}
                      onChange={(e) => updateMetadata(key, Number(e.target.value) || 0)}
                    />
                  </div>
                );
              }
              if (typeof value === 'boolean') {
                return (
                  <div key={key} className="flex items-center gap-3 py-1">
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input type="checkbox" checked={value} onChange={(e) => updateMetadata(key, e.target.checked)} className="sr-only peer" />
                      <div className="w-9 h-5 bg-[#f0e8d8] peer-focus:ring-2 peer-focus:ring-accent-primary/30 rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-gray-400 after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-accent-primary/30 peer-checked:after:bg-accent-primary"></div>
                    </label>
                    <span className="text-xs text-[#9e8b66]">{key}</span>
                  </div>
                );
              }
              return (
                <div key={key} className="flex flex-col gap-1">
                  <label className="text-xs text-[#9e8b66]">{key}</label>
                  <input
                    className={inputClass}
                    value={String(value || '')}
                    onChange={(e) => updateMetadata(key, e.target.value)}
                  />
                </div>
              );
            })}
            <AddFieldButton path={['_metadata']} target="metadata" />
          </div>
        )}
      </div>
    );
  };

  const removeFileFromDb = async (dbId: string) => {
    try {
      await axios.delete(`${API_BASE}/files/${dbId}`);
      fetchDbFileList();
    } catch (error) {
      console.error('Failed to remove JSON file from database:', error);
      showToast('Failed to remove file', 3000);
    }
  };

  const removeFile = (index: number) => {
    const cat = categories[index];
    if (cat?._dbId) removeFileFromDb(cat._dbId);
    setCategories(prev => {
      const updated = prev.filter((_, i) => i !== index);
      if (updated.length === 0) {
        setActiveTab(0);
        setActiveProduct(0);
      } else if (activeTab >= updated.length) {
        setActiveTab(updated.length - 1);
        setActiveProduct(0);
      }
      return updated;
    });
  };

  const openDbFile = async (dbFile: DbFileSummary) => {
    const alreadyLoaded = categories.findIndex(c => c._dbId === dbFile.id);
    if (alreadyLoaded >= 0) {
      setActiveTab(alreadyLoaded);
      setActiveProduct(0);
      setFileListView(false);
      return;
    }
    try {
      const res = await axios.get(`${API_BASE}/files/${dbFile.id}`);
      const data = res.data.json_content;
      const cat: CategoryData = {
        metadata: data.metadata || {},
        products: data.products || [],
        _fileName: res.data.filename,
        _originalProducts: JSON.stringify(data.products || []),
        _dbId: res.data.id,
      };
      setCategories(prev => {
        const newIdx = prev.length;
        setActiveTab(newIdx);
        setActiveProduct(0);
        return [...prev, cat];
      });
      setFileListView(false);
    } catch {
      showToast('Failed to load file', 3000);
    }
  };

  if (categories.length === 0 || fileListView) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="mb-4 md:mb-8">
          <h1 className="text-xl md:text-2xl font-bold text-[#0f1419] mb-1 md:mb-2">JSON Product Editor</h1>
          <p className="text-sm md:text-base text-[#9e8b66]">Load product catalog JSON files to edit. All fields are auto-detected.</p>
        </div>

        <div
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={(e) => { e.preventDefault(); setIsDragging(false); }}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-xl p-6 md:p-10 text-center cursor-pointer transition-all duration-200 ${
            isDragging
              ? 'border-accent-primary bg-accent-primary/5'
              : 'border-[#5b4824]/12 hover:border-[#5b4824]/15 bg-[#fefbf0]'
          }`}
        >
          <input ref={fileInputRef} type="file" multiple accept=".json" className="hidden" onChange={(e) => e.target.files && handleFiles(e.target.files)} />
          <svg className="w-10 h-10 md:w-12 md:h-12 mx-auto mb-3 text-neutral-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
          <p className="text-base md:text-lg font-medium text-[#0f1419] mb-1">Drop JSON files here or click to browse</p>
          <p className="text-xs md:text-sm text-neutral-500">Accepts multiple .json product catalog files</p>
        </div>

        {loadErrors.length > 0 && (
          <div className="mt-4 bg-red-500/10 border border-red-500/20 rounded-lg p-4">
            <p className="text-sm font-medium text-red-400 mb-1">Some files could not be loaded:</p>
            {loadErrors.map((err, i) => (
              <p key={i} className="text-xs text-red-400/80">{err}</p>
            ))}
          </div>
        )}

        {loadingFiles && (
          <div className="mt-6 text-center py-8">
            <div className="w-6 h-6 border-2 border-accent-primary border-t-transparent rounded-full animate-spin mx-auto mb-2" />
            <p className="text-sm text-neutral-500">Loading files...</p>
          </div>
        )}

        {!loadingFiles && dbFiles.length > 0 && (
          <div className="mt-6">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-3">
              <h2 className="text-sm font-semibold text-[#5f471d] uppercase tracking-wider">Saved Files ({dbFiles.length})</h2>
              <button
                onClick={clearAllFiles}
                className="w-full sm:w-auto px-3 py-1.5 bg-red-500/10 text-red-400 rounded-lg hover:bg-red-500/20 border border-red-500/20 text-xs"
              >
                Clear All
              </button>
            </div>
            <div className="space-y-2">
              {dbFiles.map((f) => {
                const inMemory = categories.find(c => c._dbId === f.id);
                const hasUnsaved = inMemory ? JSON.stringify(inMemory.products) !== inMemory._originalProducts : false;
                return (
                  <div
                    key={f.id}
                    className="flex items-start sm:items-center gap-3 bg-[#f7eede] border border-[#5b4824]/12 rounded-lg p-3 hover:border-[#5b4824]/15 transition-colors group"
                  >
                    <div className="w-10 h-10 rounded-lg bg-accent-primary/10 flex items-center justify-center shrink-0">
                      <svg className="w-5 h-5 text-accent-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                    </div>
                    <button
                      onClick={() => openDbFile(f)}
                      className="flex-1 text-left min-w-0"
                    >
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-[#0f1419] truncate">{f.filename}</span>
                        {hasUnsaved && (
                          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-yellow-500/20 text-yellow-400 border border-yellow-500/30 shrink-0">
                            <span className="w-1 h-1 rounded-full bg-yellow-400 animate-pulse" />
                            Modified
                          </span>
                        )}
                      </div>
                      <div className="flex flex-wrap items-center gap-2 sm:gap-3 mt-0.5">
                        <span className="text-xs text-neutral-500">{f.product_count} product{f.product_count !== 1 ? 's' : ''}</span>
                        {f.group_name && <span className="text-xs text-[#b5a382]">| {f.group_name}</span>}
                      </div>
                    </button>
                    <button
                      onClick={async (e) => { e.stopPropagation(); await removeFileFromDb(f.id); const idx = categories.findIndex(c => c._dbId === f.id); if (idx >= 0) removeFile(idx); }}
                      className="p-2 text-[#b5a382] hover:text-red-400 transition-colors opacity-100 md:opacity-0 md:group-hover:opacity-100 shrink-0"
                      title="Remove file"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {saveToast && (
          <div className="fixed bottom-4 left-4 right-4 sm:left-auto sm:right-6 sm:bottom-6 z-50 px-4 py-3 rounded-lg bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-sm font-medium shadow-lg flex items-center gap-2">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            {saveToast}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3 md:gap-4">
      <div className="flex flex-col gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <button
            onClick={() => setFileListView(true)}
            className="p-2 text-[#9e8b66] hover:text-[#0f1419] hover:bg-[#5b4824]/8 rounded-lg transition-colors shrink-0"
            title="Back to files"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <h1 className="text-base md:text-xl font-bold text-[#0f1419] truncate">{currentCategory?._fileName || 'JSON Editor'}</h1>
          {hasChanges && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] md:text-xs font-medium bg-yellow-500/20 text-yellow-400 border border-yellow-500/30 shrink-0">
              <span className="w-1.5 h-1.5 rounded-full bg-yellow-400 animate-pulse" />
              <span className="hidden sm:inline">Unsaved</span>
            </span>
          )}
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <button onClick={saveToDb} className="w-full sm:w-auto px-3 py-2 bg-emerald-500/10 text-emerald-400 rounded-lg hover:bg-emerald-500/20 border border-emerald-500/20 text-xs md:text-sm font-medium flex items-center justify-center gap-1.5">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            Save
          </button>
          <button onClick={resetCurrentProduct} className="w-full sm:w-auto px-3 py-2 bg-[#5b4824]/5 text-[#5f471d] rounded-lg hover:bg-[#5b4824]/8 border border-[#5b4824]/12 text-xs md:text-sm">Reset</button>
          <button onClick={downloadCurrent} className="w-full sm:w-auto px-3 py-2 bg-accent-primary/10 text-accent-primary rounded-lg hover:bg-accent-primary/20 border border-accent-primary/20 text-xs md:text-sm font-medium flex items-center justify-center gap-1.5">
            <span className="hidden sm:inline">Download</span>
            <svg className="w-4 h-4 sm:hidden" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
          </button>
          <button onClick={downloadAll} className="w-full sm:w-auto px-3 py-2 bg-accent-primary text-dark-900 rounded-lg font-medium hover:bg-accent-primary/90 text-xs md:text-sm">
            <span className="hidden sm:inline">Download All</span>
            <span className="sm:hidden">All</span>
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

      {currentCategory && (
        <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-thin">
          <div className="px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap flex items-center gap-2 bg-accent-primary/10 text-accent-primary border border-accent-primary/20">
            {String((currentCategory.metadata as Record<string, unknown>).group_name || currentCategory._fileName)}
            <span className="text-xs px-1.5 py-0.5 rounded-full bg-accent-primary/20 text-accent-primary">
              {currentCategory.products.length}
            </span>
          </div>
        </div>
      )}

      <div className="bg-[#fefbf0] border border-[#5b4824]/8 rounded-xl p-3 md:p-4">
        <div className="flex flex-col gap-3">
          <div className="flex items-center gap-2 w-full min-w-0">
            <button onClick={() => setActiveProduct(Math.max(0, activeProduct - 1))} disabled={activeProduct === 0} className="p-1.5 md:p-2 rounded-lg bg-[#5b4824]/5 hover:bg-[#5b4824]/8 disabled:opacity-30 disabled:cursor-not-allowed text-[#5f471d] transition-colors shrink-0">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" /></svg>
            </button>
            <span className="text-xs md:text-sm text-[#9e8b66] tabular-nums shrink-0">
              {products.length > 0 ? `${activeProduct + 1}/${products.length}` : '0/0'}
            </span>
            <button onClick={() => setActiveProduct(Math.min(products.length - 1, activeProduct + 1))} disabled={activeProduct >= products.length - 1} className="p-1.5 md:p-2 rounded-lg bg-[#5b4824]/5 hover:bg-[#5b4824]/8 disabled:opacity-30 disabled:cursor-not-allowed text-[#5f471d] transition-colors shrink-0">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" /></svg>
            </button>
            <select
              value={activeProduct}
              onChange={(e) => setActiveProduct(Number(e.target.value))}
              className="flex-1 min-w-0 bg-[#f7eede] border border-[#5b4824]/12 rounded-lg px-2 md:px-3 py-2 text-[#0f1419] text-xs md:text-sm focus:border-accent-primary focus:ring-1 focus:ring-accent-primary/30 truncate"
            >
              {products.map((p, i) => (
                <option key={i} value={i}>{getProductLabel(p)}</option>
              ))}
            </select>
          </div>
          <div className="relative w-full">
            <svg className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-neutral-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              className="w-full bg-[#f7eede] border border-[#5b4824]/12 rounded-lg pl-9 pr-4 py-2 text-[#0f1419] text-xs md:text-sm placeholder-neutral-500 focus:border-accent-primary focus:ring-1 focus:ring-accent-primary/30"
              placeholder="Search by SKU or name..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
        </div>
        {searchQuery && (
          <div className="mt-3 max-h-48 overflow-y-auto space-y-1">
            {filteredProducts.length === 0 ? (
              <p className="text-sm text-neutral-500 py-2">No products found</p>
            ) : (
              filteredProducts.map(({ product, originalIndex }) => (
                <button
                  key={originalIndex}
                  onClick={() => { setActiveProduct(originalIndex); setSearchQuery(''); }}
                  className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                    originalIndex === activeProduct ? 'bg-accent-primary/10 text-accent-primary' : 'text-[#5f471d] hover:bg-[#5b4824]/5'
                  }`}
                >
                  {getProductLabel(product)}
                </button>
              ))
            )}
          </div>
        )}
      </div>

      {currentProduct && (
        <div className="space-y-4">
          {renderMetadataSection()}
          {renderPrimitiveFields()}
          {objectKeys.map(key => renderObjectSection(key))}
        </div>
      )}

      {saveToast && (
        <div className="fixed bottom-4 left-4 right-4 sm:left-auto sm:right-6 sm:bottom-6 z-50 px-4 py-3 rounded-lg bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-sm font-medium shadow-lg animate-fade-in flex items-center gap-2">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
          {saveToast}
        </div>
      )}

    </div>
  );
}
