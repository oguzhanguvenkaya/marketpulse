# Faz 1: Kritik Guvenlik ve Runtime Bug Fix — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 6 kritik guvenlik acigi ve runtime bug'i fix'leyerek uygulamayi guvenli ve stabil hale getirmek.

**Architecture:** Backend (FastAPI/Python) ve Frontend (React/Vite/TypeScript) uzerinde minimal, hedefli degisiklikler. Scraping motoru hicbir maddeden etkilenmez. Tum degisiklikler Replit Autoscale uyumludur.

**Tech Stack:** Python 3, FastAPI, SQLAlchemy, React 18, TypeScript, Vite, Axios, Tailwind CSS

---

## Task 1: SellerSnapshot Bug Fix (1.3)

**Files:**
- Modify: `backend/app/api/store_product_routes.py:532`

**Step 1: Verify the bug exists**

Run: `grep -n "fetched_at" backend/app/api/store_product_routes.py`
Expected: Line 532 shows `SellerSnapshot.fetched_at.desc()`

**Step 2: Verify correct field name in model**

Run: `grep -n "snapshot_date" backend/app/db/models.py`
Expected: Line ~208 shows `snapshot_date = Column(DateTime, ...)`

**Step 3: Fix the field name**

In `backend/app/api/store_product_routes.py` line 532, change:

```python
# BEFORE:
).order_by(SellerSnapshot.fetched_at.desc()).first()

# AFTER:
).order_by(SellerSnapshot.snapshot_date.desc()).first()
```

**Step 4: Verify no other fetched_at references remain**

Run: `grep -rn "fetched_at" backend/`
Expected: ZERO results

**Step 5: Commit**

```bash
git add backend/app/api/store_product_routes.py
git commit -m "fix: use correct SellerSnapshot.snapshot_date field instead of fetched_at"
```

---

## Task 2: URL Scraper Silent Failure Fix (1.4)

**Files:**
- Modify: `backend/app/api/url_scraper_routes.py:351-352`

**Step 1: Verify the bare except exists**

Run: `grep -n "except:" backend/app/api/url_scraper_routes.py`
Expected: Line 351 shows bare `except:`

**Step 2: Fix the silent failure**

In `backend/app/api/url_scraper_routes.py` lines 351-352, change:

```python
# BEFORE (lines 351-352):
        except:
            pass

# AFTER:
        except Exception as e:
            logger.critical(f"[JOB {job_id[:8]}] Failed to mark job as failed: {e}", exc_info=True)
            try:
                db.rollback()
            except Exception:
                pass
```

**Step 3: Verify no bare except remains in this file**

Run: `grep -n "^[[:space:]]*except:[[:space:]]*$" backend/app/api/url_scraper_routes.py`
Expected: ZERO results

**Step 4: Commit**

```bash
git add backend/app/api/url_scraper_routes.py
git commit -m "fix: log and rollback on job failure instead of silent except:pass in url_scraper"
```

---

## Task 3: Transcript Silent Failure Fix (1.5)

**Files:**
- Modify: `backend/app/api/transcript_routes.py:366-367`

**Step 1: Verify the bare except exists**

Run: `grep -n "except:" backend/app/api/transcript_routes.py`
Expected: Line 366 shows bare `except:`

**Step 2: Fix the silent failure**

In `backend/app/api/transcript_routes.py` lines 366-367, change:

```python
# BEFORE (lines 366-367):
        except:
            pass

# AFTER:
        except Exception as e:
            logger.critical(f"[TRANSCRIPT {job_id[:8]}] Failed to mark job as failed: {e}", exc_info=True)
            try:
                db.rollback()
            except Exception:
                pass
```

**Step 3: Verify no bare except remains in this file**

Run: `grep -n "^[[:space:]]*except:[[:space:]]*$" backend/app/api/transcript_routes.py`
Expected: ZERO results

**Step 4: Commit**

```bash
git add backend/app/api/transcript_routes.py
git commit -m "fix: log and rollback on job failure instead of silent except:pass in transcript"
```

---

## Task 4: DB Init Race Condition Fix (1.7)

**Files:**
- Modify: `backend/app/main.py:42-45`

**Step 1: Read the current lifespan function**

Read `backend/app/main.py` lines 27-46 to understand full context.

**Step 2: Remove thread, call _init_db synchronously**

In `backend/app/main.py`, change the lifespan function (lines 42-45):

```python
# BEFORE (lines 42-45):
    t = threading.Thread(target=_init_db, daemon=True)
    t.start()

    yield

# AFTER:
    _init_db()

    yield
```

**Step 3: Remove unused threading import**

Check if `threading` is used elsewhere in the file:
Run: `grep -n "threading" backend/app/main.py`

If only used for the removed code, remove the import:
```python
# Remove this line:
import threading
```

**Step 4: Verify _init_db is called synchronously**

Run: `grep -n "threading\|Thread\|\.start()" backend/app/main.py`
Expected: ZERO results (no threading references)

Run: `grep -n "_init_db()" backend/app/main.py`
Expected: One result in lifespan function showing direct call

**Step 5: Commit**

```bash
git add backend/app/main.py
git commit -m "fix: run DB init synchronously to prevent race condition on cold start"
```

---

## Task 5: Path Traversal Fix (1.1)

**Files:**
- Modify: `backend/app/main.py:140-142`

**Step 1: Read the current serve_spa function**

Read `backend/app/main.py` lines 130-146.

**Step 2: Add path traversal protection**

In `backend/app/main.py`, the `serve_spa` function already uses `os.path`. Add `pathlib.Path` import at the top of the file (near other imports) if not already present:

```python
from pathlib import Path
```

Then change lines 140-142:

```python
# BEFORE (lines 140-142):
        file_path = os.path.join(frontend_dist, full_path)
        if full_path and os.path.isfile(file_path):
            return FileResponse(file_path)

# AFTER:
        frontend_root = Path(frontend_dist).resolve()
        requested = (frontend_root / full_path).resolve()
        if full_path and requested.is_file() and str(requested).startswith(str(frontend_root)):
            return FileResponse(str(requested))
```

**Step 3: Verify the fix with grep**

Run: `grep -n "os.path.join(frontend_dist, full_path)" backend/app/main.py`
Expected: ZERO results (old vulnerable code removed)

Run: `grep -n "frontend_root" backend/app/main.py`
Expected: Lines showing the new resolve + startswith pattern

**Step 4: Commit**

```bash
git add backend/app/main.py
git commit -m "fix: prevent path traversal in SPA static file handler via resolve+boundary check"
```

---

## Task 6: API Key Exposure Fix + Modal (1.2)

Bu task en karmasik olani — 4 alt adimda uygulanir.

### Task 6a: API interceptor'lari olustur

**Files:**
- Modify: `frontend/src/services/api.ts:8-11`

**Step 1: Remove VITE_INTERNAL_API_KEY from api.ts**

In `frontend/src/services/api.ts`, remove lines 8-11:

```typescript
// REMOVE these lines (8-11):
const internalApiKey = import.meta.env.VITE_INTERNAL_API_KEY;
if (internalApiKey) {
  api.defaults.headers.common['X-API-Key'] = internalApiKey;
}
```

**Step 2: Add request interceptor after the `api` instance creation (after line 6)**

```typescript
// Request interceptor: attach API key from sessionStorage
api.interceptors.request.use((config) => {
  const apiKey = sessionStorage.getItem('mp_api_key');
  if (apiKey) {
    config.headers['X-API-Key'] = apiKey;
  }
  return config;
});
```

**Step 3: Add response interceptor for 401/403**

```typescript
// Response interceptor: trigger API key prompt on auth failure
let isPromptingApiKey = false;

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (
      !isPromptingApiKey &&
      [401, 403].includes(error.response?.status)
    ) {
      isPromptingApiKey = true;
      window.dispatchEvent(new CustomEvent('mp:api-key-required'));

      return new Promise((resolve, reject) => {
        const handler = (e: Event) => {
          window.removeEventListener('mp:api-key-set', handler);
          isPromptingApiKey = false;
          const key = (e as CustomEvent).detail;
          if (key) {
            error.config.headers['X-API-Key'] = key;
            resolve(api.request(error.config));
          } else {
            reject(error);
          }
        };
        window.addEventListener('mp:api-key-set', handler);
      });
    }
    return Promise.reject(error);
  }
);
```

**Step 4: Verify VITE_INTERNAL_API_KEY is gone from api.ts**

Run: `grep -n "VITE_INTERNAL_API_KEY" frontend/src/services/api.ts`
Expected: ZERO results

**Step 5: Commit**

```bash
git add frontend/src/services/api.ts
git commit -m "fix: remove bundled API key, add sessionStorage-based interceptors"
```

---

### Task 6b: ApiKeyModal component olustur

**Files:**
- Create: `frontend/src/components/ApiKeyModal.tsx`

**Step 1: Create the modal component**

Create `frontend/src/components/ApiKeyModal.tsx`:

```tsx
import { useState, useEffect, useRef } from 'react';

export default function ApiKeyModal() {
  const [open, setOpen] = useState(false);
  const [key, setKey] = useState('');
  const [error, setError] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const handler = () => {
      setOpen(true);
      setKey('');
      setError('');
      setTimeout(() => inputRef.current?.focus(), 100);
    };
    window.addEventListener('mp:api-key-required', handler);
    return () => window.removeEventListener('mp:api-key-required', handler);
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = key.trim();
    if (!trimmed) {
      setError('API key boş olamaz');
      return;
    }
    sessionStorage.setItem('mp_api_key', trimmed);
    window.dispatchEvent(new CustomEvent('mp:api-key-set', { detail: trimmed }));
    setOpen(false);
  };

  const handleCancel = () => {
    window.dispatchEvent(new CustomEvent('mp:api-key-set', { detail: null }));
    setOpen(false);
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-xl shadow-2xl p-6 w-full max-w-sm mx-4">
        <h2 className="text-lg font-semibold text-[#0f1419] mb-2">API Key Gerekli</h2>
        <p className="text-sm text-[#9e8b66] mb-4">
          Bu islem icin API key girmeniz gerekiyor.
        </p>
        <form onSubmit={handleSubmit}>
          <input
            ref={inputRef}
            type="password"
            value={key}
            onChange={(e) => { setKey(e.target.value); setError(''); }}
            placeholder="API key giriniz"
            className="w-full px-3 py-2 border border-[#e8dfcf] rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#5f471d]/30 bg-[#fffbef]"
          />
          {error && <p className="text-red-500 text-xs mt-1">{error}</p>}
          <div className="flex gap-2 mt-4">
            <button
              type="button"
              onClick={handleCancel}
              className="flex-1 px-3 py-2 text-sm border border-[#e8dfcf] rounded-lg text-[#9e8b66] hover:bg-[#f7eede] transition-colors"
            >
              Iptal
            </button>
            <button
              type="submit"
              className="flex-1 px-3 py-2 text-sm bg-[#5f471d] text-white rounded-lg hover:bg-[#3d3427] transition-colors"
            >
              Kaydet
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
```

**Step 2: Commit**

```bash
git add frontend/src/components/ApiKeyModal.tsx
git commit -m "feat: add ApiKeyModal component for runtime API key entry"
```

---

### Task 6c: Modal'i App.tsx'e ekle

**Files:**
- Modify: `frontend/src/App.tsx`

**Step 1: Read current App.tsx**

Read `frontend/src/App.tsx` to see current structure.

**Step 2: Import and add ApiKeyModal**

Add import at the top of App.tsx (with other imports):

```typescript
import ApiKeyModal from './components/ApiKeyModal';
```

Add `<ApiKeyModal />` inside the Router, after Layout but outside Routes (or just before closing `</Router>`):

```tsx
// Inside the return JSX, add before closing </Router>:
<ApiKeyModal />
```

**Step 3: Verify import exists**

Run: `grep -n "ApiKeyModal" frontend/src/App.tsx`
Expected: Import line + JSX usage line

**Step 4: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "feat: integrate ApiKeyModal into App for runtime API key entry"
```

---

### Task 6d: .env temizligi

**Files:**
- Modify: `.env`

**Step 1: Remove VITE_INTERNAL_API_KEY from .env**

In `.env`, remove the line:

```
VITE_INTERNAL_API_KEY="mkt-agent-local-key-2024"
```

Keep `INTERNAL_API_KEY` — that is the backend-side key and is correct.

**Step 2: Verify no VITE_ key references remain in source**

Run: `grep -rn "VITE_INTERNAL_API_KEY" frontend/`
Expected: ZERO results

Run: `grep -rn "VITE_INTERNAL_API_KEY" .env`
Expected: ZERO results

**Step 3: Commit**

```bash
git add .env
git commit -m "fix: remove VITE_INTERNAL_API_KEY from env to prevent bundle exposure"
```

---

## Final Verification

After all tasks complete, run these checks:

```bash
# 1. No fetched_at references in backend
grep -rn "fetched_at" backend/

# 2. No bare except: in the two fixed files
grep -n "^[[:space:]]*except:[[:space:]]*$" backend/app/api/url_scraper_routes.py backend/app/api/transcript_routes.py

# 3. No threading in main.py
grep -n "threading\|Thread" backend/app/main.py

# 4. Path traversal protection exists
grep -n "frontend_root\|\.resolve()\|startswith" backend/app/main.py

# 5. No VITE_INTERNAL_API_KEY in frontend or .env
grep -rn "VITE_INTERNAL_API_KEY" frontend/ .env

# 6. ApiKeyModal integrated
grep -n "ApiKeyModal" frontend/src/App.tsx
```

All checks should pass with expected results as documented in each task.
