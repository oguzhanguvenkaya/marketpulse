import { useRef, useState, useMemo } from 'react';
import type { UseMyStoreReturn } from '../../hooks/useMyStore';
import { previewMyStoreCsv, type CsvPreviewResponse } from '../../services/myStoreApi';

const FIELD_LABELS: Record<string, { label: string; required?: boolean }> = {
  title: { label: 'Ürün Adı', required: true },
  barcode: { label: 'Barkod' },
  hepsiburada_sku: { label: 'Hepsiburada SKU' },
  brand: { label: 'Marka' },
  price: { label: 'Fiyat' },
  stock_code: { label: 'Stok Kodu' },
  subtitle: { label: 'Alt Başlık' },
  category: { label: 'Kategori' },
  category_path: { label: 'Kategori Yolu' },
  supplier: { label: 'Tedarikçi' },
  image_url: { label: 'Ana Görsel URL' },
  image_url_2: { label: '2. Görsel URL' },
  image_list: { label: 'Görsel Listesi' },
  web_url: { label: 'Web URL' },
  detail_html: { label: 'Açıklama (HTML)' },
  seo_link: { label: 'SEO Link' },
  meta_title: { label: 'Meta Title' },
  meta_description: { label: 'Meta Description' },
  meta_keywords: { label: 'Meta Keywords' },
};

const DB_FIELDS = Object.keys(FIELD_LABELS);
const NO_MAPPING = '—';

export default function MyStoreImportModal(props: UseMyStoreReturn) {
  const { setShowImportModal, importLoading, handleImportCsv } = props;
  const fileRef = useRef<HTMLInputElement>(null);

  // Step state
  const [step, setStep] = useState<1 | 2>(1);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [csvPreview, setCsvPreview] = useState<CsvPreviewResponse | null>(null);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [result, setResult] = useState<{ added: number; updated: number; total: number } | null>(null);
  const [error, setError] = useState('');

  const mappedCount = useMemo(
    () => DB_FIELDS.filter((f) => mapping[f] && mapping[f] !== NO_MAPPING).length,
    [mapping],
  );

  const isTitleMapped = mapping.title && mapping.title !== NO_MAPPING;

  // Step 1 → Step 2
  const handleContinue = async () => {
    if (!selectedFile) return;
    setError('');
    setPreviewLoading(true);
    try {
      const preview = await previewMyStoreCsv(selectedFile);
      setCsvPreview(preview);
      // Initialize mapping from suggested
      setMapping(preview.suggested_mapping || {});
      setStep(2);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'CSV önizleme başarısız');
    } finally {
      setPreviewLoading(false);
    }
  };

  // Step 2 → Import
  const handleSubmit = async () => {
    if (!selectedFile) return;
    setError('');
    // Clean mapping: remove NO_MAPPING entries
    const cleanMapping: Record<string, string> = {};
    for (const [field, col] of Object.entries(mapping)) {
      if (col && col !== NO_MAPPING) {
        cleanMapping[field] = col;
      }
    }
    try {
      const res = await handleImportCsv(selectedFile, cleanMapping);
      if (res) setResult(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Import başarısız');
    }
  };

  const handleMappingChange = (dbField: string, csvCol: string) => {
    setMapping((prev) => ({ ...prev, [dbField]: csvCol }));
  };

  const getPreviewValue = (dbField: string): string => {
    const csvCol = mapping[dbField];
    if (!csvCol || csvCol === NO_MAPPING || !csvPreview?.preview_rows?.[0]) return '';
    const val = csvPreview.preview_rows[0][csvCol];
    return val || '';
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="fixed inset-0 bg-black/40" onClick={() => setShowImportModal(false)} />
      <div className="card-dark rounded-2xl shadow-2xl max-w-2xl w-full p-6 relative z-10 max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-text-primary">CSV Import — Web Ürünleri</h3>
          <button onClick={() => setShowImportModal(false)} className="text-text-muted hover:text-text-primary">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Step indicator */}
        <div className="flex items-center gap-3 mb-5">
          <div className={`flex items-center gap-1.5 text-sm ${step === 1 ? 'text-accent-primary font-medium' : 'text-text-muted'}`}>
            <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${step === 1 ? 'bg-accent-primary text-white' : 'bg-surface-hover text-text-muted'}`}>1</span>
            Dosya Seç
          </div>
          <div className="h-px w-8 bg-border-primary" />
          <div className={`flex items-center gap-1.5 text-sm ${step === 2 ? 'text-accent-primary font-medium' : 'text-text-muted'}`}>
            <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${step === 2 ? 'bg-accent-primary text-white' : 'bg-surface-hover text-text-muted'}`}>2</span>
            Sütun Eşle
          </div>
        </div>

        {/* Step 1: File Select */}
        {step === 1 && (
          <>
            <p className="text-sm text-text-muted mb-4">
              CSV dosyanızı yükleyin. Sütun eşleme sonraki adımda yapılacak.
            </p>
            <div className="mb-4">
              <input
                ref={fileRef}
                type="file"
                accept=".csv"
                onChange={(e) => { setSelectedFile(e.target.files?.[0] || null); setResult(null); setError(''); }}
                className="hidden"
              />
              <button
                onClick={() => fileRef.current?.click()}
                className="w-full border-2 border-dashed border-border-primary rounded-xl p-6 text-center hover:border-accent-primary/50 transition-colors"
              >
                {selectedFile ? (
                  <div>
                    <p className="text-sm font-medium text-text-primary">{selectedFile.name}</p>
                    <p className="text-xs text-text-muted mt-1">{(selectedFile.size / 1024).toFixed(1)} KB</p>
                  </div>
                ) : (
                  <div>
                    <svg className="w-8 h-8 mx-auto text-text-muted/40 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                    </svg>
                    <p className="text-sm text-text-muted">CSV dosyası seçin</p>
                  </div>
                )}
              </button>
            </div>
            {error && <div className="mb-4 p-3 rounded-lg bg-danger/10 text-danger text-sm">{error}</div>}
            <div className="flex justify-end gap-2">
              <button onClick={() => setShowImportModal(false)} className="px-4 py-2 rounded-lg text-sm text-text-muted hover:bg-surface-hover">
                İptal
              </button>
              <button
                onClick={handleContinue}
                disabled={!selectedFile || previewLoading}
                className="btn-primary px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-50"
              >
                {previewLoading ? 'Analiz ediliyor...' : 'Devam'}
              </button>
            </div>
          </>
        )}

        {/* Step 2: Column Mapping */}
        {step === 2 && csvPreview && (
          <>
            <div className="overflow-y-auto flex-1 mb-4 max-h-[400px] border border-border-primary rounded-xl">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-surface-secondary">
                  <tr className="text-left text-text-muted text-xs">
                    <th className="px-3 py-2 font-medium">DB Alanı</th>
                    <th className="px-3 py-2 font-medium">CSV Sütunu</th>
                    <th className="px-3 py-2 font-medium">Önizleme</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-primary">
                  {DB_FIELDS.map((field) => {
                    const meta = FIELD_LABELS[field];
                    return (
                      <tr key={field} className="hover:bg-surface-hover/50">
                        <td className="px-3 py-2 whitespace-nowrap">
                          <span className="text-text-primary">{meta.label}</span>
                          {meta.required && <span className="text-danger ml-1">*</span>}
                        </td>
                        <td className="px-3 py-2">
                          <select
                            value={mapping[field] || NO_MAPPING}
                            onChange={(e) => handleMappingChange(field, e.target.value)}
                            className="w-full bg-surface-primary border border-border-primary rounded-lg px-2 py-1.5 text-sm text-text-primary focus:outline-none focus:ring-1 focus:ring-accent-primary"
                          >
                            <option value={NO_MAPPING}>— Eşleme yok —</option>
                            {csvPreview.headers.map((h) => (
                              <option key={h} value={h}>{h}</option>
                            ))}
                          </select>
                        </td>
                        <td className="px-3 py-2 text-text-muted truncate max-w-[200px]" title={getPreviewValue(field)}>
                          {getPreviewValue(field) || <span className="text-text-muted/40">—</span>}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Info line */}
            <p className="text-xs text-text-muted mb-4">
              {csvPreview.row_count} satır bulundu &bull; {mappedCount}/{DB_FIELDS.length} alan eşlendi
              {csvPreview.delimiter !== ',' && <span> &bull; Ayırıcı: <code className="bg-surface-hover px-1 rounded">{csvPreview.delimiter === ';' ? ';' : csvPreview.delimiter === '\t' ? 'TAB' : csvPreview.delimiter}</code></span>}
            </p>

            {/* Result */}
            {result && (
              <div className="mb-4 p-3 rounded-lg bg-success/10 text-success text-sm">
                {result.added} ürün eklendi, {result.updated} güncellendi (toplam: {result.total})
              </div>
            )}
            {error && <div className="mb-4 p-3 rounded-lg bg-danger/10 text-danger text-sm">{error}</div>}

            {/* Actions */}
            <div className="flex justify-between">
              <button
                onClick={() => { setStep(1); setError(''); }}
                className="px-4 py-2 rounded-lg text-sm text-text-muted hover:bg-surface-hover"
                disabled={importLoading}
              >
                &larr; Geri
              </button>
              <div className="flex gap-2">
                <button onClick={() => setShowImportModal(false)} className="px-4 py-2 rounded-lg text-sm text-text-muted hover:bg-surface-hover">
                  {result ? 'Kapat' : 'İptal'}
                </button>
                {!result && (
                  <button
                    onClick={handleSubmit}
                    disabled={!isTitleMapped || importLoading}
                    className="btn-primary px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-50"
                    title={!isTitleMapped ? 'Ürün Adı alanı eşlenmeli' : undefined}
                  >
                    {importLoading ? 'Yükleniyor...' : 'Import Et'}
                  </button>
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
