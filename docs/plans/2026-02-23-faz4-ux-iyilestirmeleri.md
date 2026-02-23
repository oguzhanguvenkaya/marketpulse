# Faz 4: UX Iyilestirmeleri — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** ErrorBoundary, sonner toast ve ozel ConfirmDialog ile 14 native alert/confirm dialogu degistirip kullanici deneyimini iyilestirmek.

**Architecture:** 3 yeni komponent (ErrorBoundary, ConfirmDialog, Toaster entegrasyonu) olusturulur. 14 native dialog (9 alert, 5 confirm) toast ve ConfirmDialog'a migrate edilir. Projenin mevcut dark tema tokenlari ve ApiKeyModal stilistigi referans alinir.

**Tech Stack:** React 19, sonner, TypeScript, Tailwind CSS (class-based dark mode)

---

## Task 1: sonner Kurulumu ve Toaster Entegrasyonu

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/src/App.tsx`

**Step 1: Install sonner**

```bash
cd /Users/projectx/Desktop/marketpulse/frontend && npm install sonner
```

**Step 2: Add Toaster to App.tsx**

`frontend/src/App.tsx` — import ekle (dosyanin basina):

```typescript
import { Toaster } from 'sonner';
```

Toaster komponentini `<Router>` icinde, `<ApiKeyModal />` yanina ekle (satir ~46 civari):

```tsx
<ApiKeyModal />
<Toaster
  position="top-right"
  toastOptions={{
    className: 'bg-[var(--surface-raised)] text-[var(--color-dark-300)] border border-[var(--surface-border)] shadow-lg',
    style: {
      fontFamily: 'Inter, sans-serif',
    },
  }}
  richColors
/>
```

**Step 3: Verify build**

```bash
cd /Users/projectx/Desktop/marketpulse/frontend && npx tsc --noEmit && npm run build
```

Expected: No errors.

---

## Task 2: ErrorBoundary Komponenti

**Files:**
- Create: `frontend/src/components/ErrorBoundary.tsx`
- Modify: `frontend/src/App.tsx`

**Step 1: Create ErrorBoundary component**

Create `frontend/src/components/ErrorBoundary.tsx`:

```tsx
import { Component, type ErrorInfo, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.setState({ errorInfo });
    console.error('ErrorBoundary caught:', error, errorInfo);
  }

  handleReload = () => {
    window.location.reload();
  };

  handleGoHome = () => {
    window.location.href = '/';
  };

  render() {
    if (this.state.hasError) {
      const isDev = import.meta.env.DEV;

      return (
        <div className="min-h-screen flex items-center justify-center bg-[var(--color-dark-900)] p-6">
          <div className="max-w-lg w-full bg-[var(--surface-raised)] border border-[var(--surface-border)] rounded-xl shadow-lg p-8 text-center">
            <div className="text-4xl mb-4">⚠</div>
            <h1 className="text-xl font-serif font-bold text-[var(--color-dark-300)] mb-2">
              Bir hata olustu
            </h1>
            <p className="text-[var(--color-dark-400)] text-sm mb-6">
              Beklenmeyen bir sorun nedeniyle bu sayfa goruntulenemiyor.
            </p>

            <div className="flex gap-3 justify-center mb-6">
              <button
                onClick={this.handleReload}
                className="px-4 py-2 rounded-lg bg-[var(--color-accent-primary)] text-white dark:text-[#0F1A17] font-medium text-sm hover:opacity-90 transition-opacity"
              >
                Sayfayi Yenile
              </button>
              <button
                onClick={this.handleGoHome}
                className="px-4 py-2 rounded-lg border border-[var(--surface-border-strong)] text-[var(--color-dark-400)] font-medium text-sm hover:bg-[var(--color-dark-800)] transition-colors"
              >
                Ana Sayfaya Don
              </button>
            </div>

            {isDev && this.state.error && (
              <details className="text-left mt-4 border-t border-[var(--surface-border)] pt-4">
                <summary className="text-xs text-[var(--color-dark-400)] cursor-pointer hover:text-[var(--color-dark-300)]">
                  Teknik Detaylar (Development)
                </summary>
                <pre className="mt-2 p-3 bg-[var(--color-dark-900)] rounded-lg text-xs text-red-400 overflow-auto max-h-48 font-mono">
                  {this.state.error.toString()}
                  {this.state.errorInfo?.componentStack}
                </pre>
              </details>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
```

**Step 2: Wrap App routes with ErrorBoundary**

`frontend/src/App.tsx` — import ekle:

```typescript
import ErrorBoundary from './components/ErrorBoundary';
```

`<Suspense>` komponentini `<ErrorBoundary>` ile sar:

```tsx
<Layout>
  <ErrorBoundary>
    <Suspense fallback={<PageSkeleton />}>
      {/* ... routes ... */}
    </Suspense>
  </ErrorBoundary>
</Layout>
```

**Step 3: Verify build**

```bash
cd /Users/projectx/Desktop/marketpulse/frontend && npx tsc --noEmit && npm run build
```

Expected: No errors.

---

## Task 3: ConfirmDialog Komponenti

**Files:**
- Create: `frontend/src/components/ConfirmDialog.tsx`

**Step 1: Create ConfirmDialog component**

Create `frontend/src/components/ConfirmDialog.tsx`:

```tsx
import { useEffect, useRef } from 'react';

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: 'danger' | 'default';
  onConfirm: () => void;
  onCancel: () => void;
}

export default function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = 'Onayla',
  cancelLabel = 'Iptal',
  variant = 'default',
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const cancelRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (open) {
      cancelRef.current?.focus();
    }
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onCancel();
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [open, onCancel]);

  if (!open) return null;

  const confirmColors =
    variant === 'danger'
      ? 'bg-[var(--color-danger,#cb5150)] text-white hover:opacity-90'
      : 'bg-[var(--color-accent-primary)] text-white dark:text-[#0F1A17] hover:opacity-90';

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onClick={onCancel}
    >
      <div
        className="bg-[var(--surface-raised)] border border-[var(--surface-border)] rounded-xl shadow-2xl p-6 w-full max-w-sm mx-4"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="text-lg font-serif font-bold text-[var(--color-dark-300)] mb-2">
          {title}
        </h3>
        <p className="text-sm text-[var(--color-dark-400)] mb-6">{message}</p>
        <div className="flex gap-2">
          <button
            ref={cancelRef}
            onClick={onCancel}
            className="flex-1 px-4 py-2 rounded-lg border border-[var(--surface-border-strong)] text-[var(--color-dark-400)] text-sm font-medium hover:bg-[var(--color-dark-800)] transition-colors"
          >
            {cancelLabel}
          </button>
          <button
            onClick={onConfirm}
            className={`flex-1 px-4 py-2 rounded-lg text-sm font-medium transition-opacity ${confirmColors}`}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
```

**Step 2: Verify build**

```bash
cd /Users/projectx/Desktop/marketpulse/frontend && npx tsc --noEmit && npm run build
```

Expected: No errors.

---

## Task 4: usePriceMonitor.ts — 9 Native Dialog Degisimi

**Files:**
- Modify: `frontend/src/hooks/usePriceMonitor.ts`
- Modify: `frontend/src/pages/PriceMonitor.tsx` (veya PriceMonitor komponent dosyasi — ConfirmDialog state'i icin)

**Envanter (usePriceMonitor.ts):**

| Satir | Tip | Mesaj | Degisiklik |
|-------|-----|-------|------------|
| 240 | alert | `"${result.added} products added..."` | → `toast.success(...)` |
| 246 | alert | `'JSON parse error: ' + message` | → `toast.error(...)` |
| 262 | alert | `'Could not start price fetch'` | → `toast.error(...)` |
| 273 | alert | `'Could not stop fetch'` | → `toast.error(...)` |
| 286 | alert | `'Could not fetch price'` | → `toast.error(...)` |
| 291 | confirm | `'Are you sure you want to delete this product?'` | → `ConfirmDialog` callback pattern |
| 311 | alert | `'Export failed'` | → `toast.error(...)` |
| 327 | alert | `result.message` | → `toast.success(...)` |
| 334 | alert | `'Delete failed'` | → `toast.error(...)` |

**Step 1: Import toast in usePriceMonitor.ts**

Dosyanin basina ekle:

```typescript
import { toast } from 'sonner';
```

**Step 2: Replace 8 alert() calls with toast**

Her `alert(...)` satiri icin:
- Basari mesajlari → `toast.success(...)`
- Hata mesajlari → `toast.error(...)`

Degisiklikler:

```typescript
// Satir 240 — import basari
// ONCE: alert(`${result.added} products added, ${result.updated} updated (${result.platform}).`);
// SONRA:
toast.success(`${result.added} products added, ${result.updated} updated (${result.platform}).`);

// Satir 246 — JSON parse error
// ONCE: alert('JSON parse error: ' + message);
// SONRA:
toast.error('JSON parse error: ' + message);

// Satir 262 — fetch baslatilamadi
// ONCE: alert('Could not start price fetch');
// SONRA:
toast.error('Could not start price fetch');

// Satir 273 — fetch durdurulamadi
// ONCE: alert('Could not stop fetch');
// SONRA:
toast.error('Could not stop fetch');

// Satir 286 — tekil fetch hatasi
// ONCE: alert('Could not fetch price');
// SONRA:
toast.error('Could not fetch price');

// Satir 311 — export hatasi
// ONCE: alert('Export failed');
// SONRA:
toast.error('Export failed');

// Satir 327 — bulk delete basari
// ONCE: alert(result.message);
// SONRA:
toast.success(result.message);

// Satir 334 — bulk delete hatasi
// ONCE: alert('Delete failed');
// SONRA:
toast.error('Delete failed');
```

**Step 3: Convert confirm() to callback pattern for handleDelete**

Satir 291 `confirm(...)` icin: `handleDelete` fonksiyonunu, confirm yerine bir callback pattern'e cevir.

ONCE (usePriceMonitor.ts ~satir 289-300):
```typescript
const handleDelete = useCallback(async (id: string) => {
    if (!confirm('Are you sure you want to delete this product?')) return;
    // ... delete logic
}, [...]);
```

SONRA:
```typescript
const [deleteTarget, setDeleteTarget] = useState<string | null>(null);

const handleDeleteRequest = useCallback((id: string) => {
    setDeleteTarget(id);
}, []);

const handleDeleteConfirm = useCallback(async () => {
    if (!deleteTarget) return;
    const id = deleteTarget;
    setDeleteTarget(null);
    try {
        await deleteMonitoredProduct(id);
        setSelectedProduct(null);
        setSelectedBrand(null);
        loadProducts();
        toast.success('Urun silindi');
    } catch {
        toast.error('Delete failed');
    }
}, [deleteTarget, loadProducts]);

const handleDeleteCancel = useCallback(() => {
    setDeleteTarget(null);
}, []);
```

Hook'un return degerine ekle:
```typescript
return {
    // ... mevcut return degerleri ...
    deleteTarget,
    handleDeleteRequest,  // eski handleDelete yerine
    handleDeleteConfirm,
    handleDeleteCancel,
};
```

**Step 4: Update PriceMonitor component to use ConfirmDialog**

PriceMonitor komponentinde (usePriceMonitor hook'unu kullanan yer):

```tsx
import ConfirmDialog from '../components/ConfirmDialog';

// Hook'tan yeni degerleri al:
const {
    // ... mevcut degerler ...
    deleteTarget,
    handleDeleteRequest,
    handleDeleteConfirm,
    handleDeleteCancel,
} = usePriceMonitor();

// JSX'e ConfirmDialog ekle (return'un sonuna):
<ConfirmDialog
    open={deleteTarget !== null}
    title="Urunu Sil"
    message="Bu urunu silmek istediginizden emin misiniz?"
    confirmLabel="Sil"
    cancelLabel="Iptal"
    variant="danger"
    onConfirm={handleDeleteConfirm}
    onCancel={handleDeleteCancel}
/>
```

Eski `handleDelete` kullanimlarini `handleDeleteRequest` ile degistir.

**Step 5: Verify build**

```bash
cd /Users/projectx/Desktop/marketpulse/frontend && npx tsc --noEmit && npm run build
```

Expected: No errors.

---

## Task 5: useCategoryExplorer.ts — 4 Native Dialog Degisimi

**Files:**
- Modify: `frontend/src/hooks/useCategoryExplorer.ts`
- Modify: `frontend/src/pages/CategoryExplorer.tsx` (ConfirmDialog state'i icin)

**Envanter (useCategoryExplorer.ts):**

| Satir | Tip | Mesaj | Degisiklik |
|-------|-----|-------|------------|
| 393 | confirm | `'Are you sure you want to delete this product?'` | → ConfirmDialog callback |
| 400 | alert | `err?.response?.data?.detail \|\| 'Delete failed'` | → `toast.error(...)` |
| 406 | confirm | `` `Delete ${selectedForDetail.size} selected products?` `` | → ConfirmDialog callback |
| 413 | alert | `err?.response?.data?.detail \|\| 'Bulk delete failed'` | → `toast.error(...)` |

**Step 1: Import toast**

```typescript
import { toast } from 'sonner';
```

**Step 2: Replace 2 alert() calls with toast**

```typescript
// Satir 400 — delete hatasi
// ONCE: alert(err?.response?.data?.detail || 'Delete failed');
// SONRA:
toast.error(err?.response?.data?.detail || 'Delete failed');

// Satir 413 — bulk delete hatasi
// ONCE: alert(err?.response?.data?.detail || 'Bulk delete failed');
// SONRA:
toast.error(err?.response?.data?.detail || 'Bulk delete failed');
```

**Step 3: Convert 2 confirm() calls to callback pattern**

Ayni Task 4 pattern'i: `deleteTarget` state'i yerine burada 2 farkli confirm var:

```typescript
const [confirmAction, setConfirmAction] = useState<{
    type: 'delete-single' | 'delete-bulk';
    message: string;
} | null>(null);

// handleDeleteProduct — satir 393
const handleDeleteProductRequest = useCallback((productId: string) => {
    setConfirmAction({
        type: 'delete-single',
        message: 'Bu urunu silmek istediginizden emin misiniz?',
    });
    // productId'yi state'e kaydet (mevcut selectedForDetail veya ayri state)
}, []);

// handleBulkDelete — satir 406
const handleBulkDeleteRequest = useCallback(() => {
    setConfirmAction({
        type: 'delete-bulk',
        message: `${selectedForDetail.size} secili urunu silmek istediginizden emin misiniz?`,
    });
}, [selectedForDetail.size]);

const handleConfirmAction = useCallback(async () => {
    if (!confirmAction) return;
    const action = confirmAction;
    setConfirmAction(null);

    if (action.type === 'delete-single') {
        // mevcut tek silme logic'i (try/catch + toast.error)
    } else if (action.type === 'delete-bulk') {
        // mevcut toplu silme logic'i (try/catch + toast.error)
    }
}, [confirmAction, /* diger dependencies */]);

const handleCancelAction = useCallback(() => {
    setConfirmAction(null);
}, []);
```

Hook return'una ekle:
```typescript
return {
    // ... mevcut ...
    confirmAction,
    handleDeleteProductRequest,
    handleBulkDeleteRequest,
    handleConfirmAction,
    handleCancelAction,
};
```

**Step 4: Update CategoryExplorer component to use ConfirmDialog**

```tsx
import ConfirmDialog from '../components/ConfirmDialog';

const {
    confirmAction,
    handleDeleteProductRequest,
    handleBulkDeleteRequest,
    handleConfirmAction,
    handleCancelAction,
} = useCategoryExplorer();

// JSX'e ekle:
<ConfirmDialog
    open={confirmAction !== null}
    title="Silme Onayi"
    message={confirmAction?.message ?? ''}
    confirmLabel="Sil"
    cancelLabel="Iptal"
    variant="danger"
    onConfirm={handleConfirmAction}
    onCancel={handleCancelAction}
/>
```

**Step 5: Verify build**

```bash
cd /Users/projectx/Desktop/marketpulse/frontend && npx tsc --noEmit && npm run build
```

Expected: No errors.

---

## Task 6: UrlScraper.tsx ve VideoTranscripts.tsx — 2 Native Dialog Degisimi

**Files:**
- Modify: `frontend/src/pages/UrlScraper.tsx`
- Modify: `frontend/src/pages/VideoTranscripts.tsx`

**Envanter:**

| Dosya | Satir | Tip | Mesaj |
|-------|-------|-----|-------|
| UrlScraper.tsx | 175 | confirm | `'Are you sure you want to delete this job?'` |
| VideoTranscripts.tsx | 177 | confirm | `'Are you sure you want to delete this job?'` |

**Step 1: UrlScraper.tsx — confirm → ConfirmDialog**

```tsx
import { useState } from 'react';
import ConfirmDialog from '../components/ConfirmDialog';

// State ekle:
const [deleteJobId, setDeleteJobId] = useState<string | null>(null);

// handleDelete fonksiyonunu ikiye bol:
// ONCE:
// const handleDelete = async (jobId: string) => {
//     if (!confirm('Are you sure you want to delete this job?')) return;
//     await deleteScrapeJob(jobId);
//     ...
// };

// SONRA:
const handleDeleteRequest = (jobId: string) => {
    setDeleteJobId(jobId);
};

const handleDeleteConfirm = async () => {
    if (!deleteJobId) return;
    const jobId = deleteJobId;
    setDeleteJobId(null);
    try {
        await deleteScrapeJob(jobId);
        setExpandedJobId(null);
        setJobDetail(null);
        fetchJobs();
    } catch {
        toast.error('Silme islemi basarisiz');
    }
};

// JSX'e ekle:
<ConfirmDialog
    open={deleteJobId !== null}
    title="Gorevi Sil"
    message="Bu gorevi silmek istediginizden emin misiniz?"
    confirmLabel="Sil"
    cancelLabel="Iptal"
    variant="danger"
    onConfirm={handleDeleteConfirm}
    onCancel={() => setDeleteJobId(null)}
/>
```

Eski `handleDelete(jobId)` cagrIlarini `handleDeleteRequest(jobId)` ile degistir.

**Step 2: VideoTranscripts.tsx — ayni pattern**

UrlScraper ile birebir ayni pattern:

```tsx
import { useState } from 'react';
import ConfirmDialog from '../components/ConfirmDialog';

const [deleteJobId, setDeleteJobId] = useState<string | null>(null);

const handleDeleteRequest = (jobId: string) => {
    setDeleteJobId(jobId);
};

const handleDeleteConfirm = async () => {
    if (!deleteJobId) return;
    const jobId = deleteJobId;
    setDeleteJobId(null);
    try {
        await deleteTranscriptJob(jobId);
        setExpandedJobId(null);
        setJobDetail(null);
        fetchJobs();
    } catch {
        toast.error('Silme islemi basarisiz');
    }
};

// JSX'e ekle:
<ConfirmDialog
    open={deleteJobId !== null}
    title="Gorevi Sil"
    message="Bu gorevi silmek istediginizden emin misiniz?"
    confirmLabel="Sil"
    cancelLabel="Iptal"
    variant="danger"
    onConfirm={handleDeleteConfirm}
    onCancel={() => setDeleteJobId(null)}
/>
```

**Step 3: Verify build**

```bash
cd /Users/projectx/Desktop/marketpulse/frontend && npx tsc --noEmit && npm run build
```

Expected: No errors.

---

## Final Verification

```bash
# 1. Hic native dialog kalmadi mi?
cd /Users/projectx/Desktop/marketpulse && grep -rn "alert\(\|confirm(" frontend/src/ --include="*.ts" --include="*.tsx" | grep -v node_modules | grep -v "// "

# Expected: SIFIR sonuc (ApiKeyModal'daki CustomEvent handler haric)

# 2. Full build
cd /Users/projectx/Desktop/marketpulse/frontend && npm run build

# Expected: Build basarili

# 3. Lint check
cd /Users/projectx/Desktop/marketpulse && make lint

# Expected: Clean (veya sadece backend uyarilari)

# 4. Backend testleri hala gecerli
cd /Users/projectx/Desktop/marketpulse && make test

# Expected: 22/22 PASS
```
