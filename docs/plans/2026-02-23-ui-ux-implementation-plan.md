# MarketPulse UI/UX Improvements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Improve MarketPulse frontend with grouped navigation, skeleton loading, dark mode, enhanced dashboard, and component decomposition.

**Architecture:** All changes are frontend-only except one new backend endpoint for dashboard trends. We use CSS custom properties for theming, inline SVG sparklines, and React hooks for state management refactoring.

**Tech Stack:** React 19, TypeScript, Tailwind CSS v4, Vite 7, Plotly.js

---

## Task 1: Skeleton Loading System

> Must come first — other tasks depend on skeleton components.

**Files:**
- Create: `frontend/src/components/Skeleton.tsx`
- Modify: `frontend/src/App.tsx:22-28`

---

### Step 1.1: Create Skeleton primitive components

Create `frontend/src/components/Skeleton.tsx` with reusable skeleton building blocks.

```tsx
import { type ReactNode } from 'react';

function Shimmer({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div className={`relative overflow-hidden ${className}`}>
      {children}
      <div className="absolute inset-0 -translate-x-full animate-[shimmer_1.5s_infinite] bg-gradient-to-r from-transparent via-white/20 to-transparent" />
    </div>
  );
}

export function SkeletonLine({ width = 'w-full', height = 'h-4' }: { width?: string; height?: string }) {
  return <div className={`${width} ${height} rounded-lg bg-dark-600/30`} />;
}

export function SkeletonCircle({ size = 'w-10 h-10' }: { size?: string }) {
  return <div className={`${size} rounded-full bg-dark-600/30`} />;
}

export function SkeletonCard() {
  return (
    <Shimmer className="card-dark p-4 md:p-6">
      <div className="space-y-3">
        <SkeletonLine width="w-1/3" height="h-5" />
        <SkeletonLine width="w-full" />
        <SkeletonLine width="w-2/3" />
      </div>
    </Shimmer>
  );
}

export function SkeletonStatCard() {
  return (
    <Shimmer className="stat-card">
      <div className="flex items-start justify-between">
        <div className="space-y-2">
          <SkeletonLine width="w-20" height="h-8" />
          <SkeletonLine width="w-24" height="h-3" />
        </div>
        <div className="w-10 h-10 rounded-lg bg-dark-600/30" />
      </div>
    </Shimmer>
  );
}

export function SkeletonTable({ rows = 5 }: { rows?: number }) {
  return (
    <Shimmer className="card-dark overflow-hidden">
      <div className="px-4 md:px-6 py-3 md:py-4 border-b border-dark-600/20">
        <SkeletonLine width="w-40" height="h-5" />
      </div>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="px-4 md:px-6 py-3 md:py-4 border-b border-dark-600/10 flex items-center gap-4">
          <div className="w-9 h-9 rounded-lg bg-dark-600/30" />
          <div className="flex-1 space-y-2">
            <SkeletonLine width="w-1/3" height="h-4" />
            <SkeletonLine width="w-1/5" height="h-3" />
          </div>
          <SkeletonLine width="w-16" height="h-6" />
        </div>
      ))}
    </Shimmer>
  );
}

export function SkeletonChart({ height = 'h-64' }: { height?: string }) {
  return (
    <Shimmer className={`card-dark p-4 md:p-6 ${height}`}>
      <SkeletonLine width="w-32" height="h-5" />
      <div className="mt-4 flex-1 rounded-lg bg-dark-600/20 h-full" />
    </Shimmer>
  );
}

export function DashboardSkeleton() {
  return (
    <div className="space-y-5 md:space-y-6">
      <div className="space-y-1">
        <SkeletonLine width="w-32" height="h-7" />
        <SkeletonLine width="w-64" height="h-4" />
      </div>
      <SkeletonCard />
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4">
        {Array.from({ length: 4 }).map((_, i) => <SkeletonStatCard key={i} />)}
      </div>
      <SkeletonTable rows={5} />
    </div>
  );
}

export function ProductsSkeleton() {
  return (
    <div className="space-y-5">
      <div className="flex flex-col md:flex-row gap-3">
        <SkeletonLine width="flex-1" height="h-11" />
        <SkeletonLine width="w-44" height="h-11" />
        <SkeletonLine width="w-28" height="h-11" />
      </div>
      <SkeletonTable rows={8} />
    </div>
  );
}

export function PriceMonitorSkeleton() {
  return (
    <div className="space-y-5">
      <div className="flex gap-3">
        <SkeletonLine width="w-32" height="h-10" />
        <SkeletonLine width="w-32" height="h-10" />
        <SkeletonLine width="w-32" height="h-10" />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2"><SkeletonTable rows={6} /></div>
        <SkeletonCard />
      </div>
    </div>
  );
}

export default function PageSkeleton() {
  return (
    <div className="space-y-5 md:space-y-6">
      <div className="space-y-1">
        <SkeletonLine width="w-40" height="h-7" />
        <SkeletonLine width="w-72" height="h-4" />
      </div>
      <SkeletonCard />
      <SkeletonTable rows={5} />
    </div>
  );
}
```

### Step 1.2: Add shimmer animation to Tailwind config

Modify `frontend/tailwind.config.js:60-63` — add the shimmer keyframe:

```js
// Inside theme.extend.animation (line 60):
animation: {
  'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
  'glow': 'glow 2.2s ease-in-out infinite alternate',
  'shimmer': 'shimmer 1.5s infinite',
},
// Inside theme.extend.keyframes (line 64):
keyframes: {
  glow: {
    '0%': { boxShadow: '0 0 4px rgba(247, 206, 134, 0.2)' },
    '100%': { boxShadow: '0 0 16px rgba(247, 206, 134, 0.35)' },
  },
  shimmer: {
    '100%': { transform: 'translateX(100%)' },
  },
},
```

### Step 1.3: Replace PageLoader in App.tsx

Modify `frontend/src/App.tsx:1-28` — replace the spinner with the skeleton:

```tsx
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { lazy, Suspense } from 'react'
import Layout from './components/Layout'
import ApiKeyModal from './components/ApiKeyModal'
import PageSkeleton from './components/Skeleton'
import './App.css'

// ... lazy imports stay the same (lines 7-20) ...

function App() {
  return (
    <Router>
      <Layout>
        <Suspense fallback={<PageSkeleton />}>
          {/* Routes stay the same */}
```

Remove the old `PageLoader` function entirely (lines 22-28).

### Step 1.4: Verify build passes

Run: `cd frontend && npm run build`
Expected: Build succeeds with no errors.

### Step 1.5: Commit

```bash
git add frontend/src/components/Skeleton.tsx frontend/src/App.tsx frontend/tailwind.config.js
git commit -m "feat: add skeleton loading system replacing spinner"
```

---

## Task 2: Navigation Grouping (Accordion Sidebar)

**Files:**
- Modify: `frontend/src/components/Layout.tsx:21-161`

---

### Step 2.1: Refactor nav data to grouped structure

Replace the `navItems` useMemo (lines 21-83) with a grouped structure. Each existing icon SVG stays the same — only the data structure changes.

```tsx
interface NavItem {
  path: string;
  label: string;
  icon: React.ReactNode;
}

interface NavGroup {
  label: string;
  icon: React.ReactNode;
  items: NavItem[];
}

const NAV_GROUPS_KEY = 'mp_nav_groups';
```

The new data structure in the component (replacing lines 21-83):

```tsx
const navGroups = useMemo((): { standalone: NavItem; groups: NavGroup[] } => ({
  standalone: {
    path: '/', label: 'Dashboard', icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
      </svg>
    ),
  },
  groups: [
    {
      label: 'Pazaryerleri',
      icon: (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" />
        </svg>
      ),
      items: [
        { path: '/hepsiburada', label: 'Hepsiburada', icon: /* existing SVG from line 48-51 */ },
        { path: '/trendyol', label: 'Trendyol', icon: /* existing SVG from line 53-56 */ },
        { path: '/web-products', label: 'Web Products', icon: /* existing SVG from line 58-61 */ },
      ],
    },
    {
      label: 'Analiz',
      icon: (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
      ),
      items: [
        { path: '/products', label: 'Products', icon: /* existing SVG from line 27-30 */ },
        { path: '/ads', label: 'Ads', icon: /* existing SVG from line 32-36 */ },
        { path: '/price-monitor', label: 'Price Monitor', icon: /* existing SVG from line 38-41 */ },
        { path: '/sellers', label: 'Sellers', icon: /* existing SVG from line 43-46 */ },
        { path: '/category-explorer', label: 'Category Explorer', icon: /* existing SVG from line 63-66 */ },
      ],
    },
    {
      label: 'Araclar',
      icon: (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
      ),
      items: [
        { path: '/url-scraper', label: 'URL Scraper', icon: /* existing SVG from line 68-71 */ },
        { path: '/video-transcripts', label: 'Transcripts', icon: /* existing SVG from line 73-76 */ },
        { path: '/json-editor', label: 'JSON Editor', icon: /* existing SVG from line 78-81 */ },
      ],
    },
  ],
}), []);
```

> **Note to implementer:** Copy each existing icon SVG exactly from the current navItems array. The comment `/* existing SVG from line X-Y */` means copy that exact SVG element.

### Step 2.2: Add group expand/collapse state

Add after the `collapsed` state (after line 15):

```tsx
const [expandedGroups, setExpandedGroups] = useState<Set<string>>(() => {
  try {
    const saved = localStorage.getItem(NAV_GROUPS_KEY);
    return saved ? new Set(JSON.parse(saved)) : new Set(['Pazaryerleri', 'Analiz', 'Araclar']);
  } catch { return new Set(['Pazaryerleri', 'Analiz', 'Araclar']); }
});

useEffect(() => {
  try { localStorage.setItem(NAV_GROUPS_KEY, JSON.stringify([...expandedGroups])); } catch {}
}, [expandedGroups]);

const toggleGroup = (label: string) => {
  setExpandedGroups(prev => {
    const next = new Set(prev);
    next.has(label) ? next.delete(label) : next.add(label);
    return next;
  });
};
```

### Step 2.3: Auto-expand active group

Update the `activeLabel` useMemo (lines 85-88) to also auto-expand:

```tsx
const activeLabel = useMemo(() => {
  // Check standalone
  if (navGroups.standalone.path === location.pathname) return navGroups.standalone.label;
  // Check groups
  for (const group of navGroups.groups) {
    const match = group.items.find(item => item.path === location.pathname);
    if (match) {
      // Auto-expand active group
      setExpandedGroups(prev => {
        if (prev.has(group.label)) return prev;
        return new Set([...prev, group.label]);
      });
      return match.label;
    }
  }
  return 'Workspace';
}, [location.pathname, navGroups]);
```

### Step 2.4: Replace nav render section

Replace the `<nav>` content (lines 133-161) with grouped rendering:

```tsx
<nav className={`flex-1 overflow-y-auto transition-all duration-300 ${collapsed ? 'p-2' : 'p-4'}`}>
  <div className="space-y-1">
    {/* Dashboard - standalone */}
    {(() => {
      const item = navGroups.standalone;
      const isActive = location.pathname === item.path;
      return (
        <Link
          to={item.path}
          onClick={() => setMobileOpen(false)}
          title={collapsed ? item.label : undefined}
          className={`nav-item flex items-center rounded-xl text-sm font-semibold transition-all duration-200 ${
            collapsed ? 'justify-center px-0 py-3' : 'gap-3 px-4 py-3'
          } ${isActive ? 'nav-item-active text-[#3a2d14]' : 'text-[#7a6b4e]'}`}
        >
          <span className={`flex-shrink-0 ${isActive ? 'text-[#5b4824]' : 'text-[#9e8b66]'}`}>{item.icon}</span>
          {!collapsed && (
            <>
              <span className="truncate">{item.label}</span>
              {isActive && <div className="ml-auto w-1.5 h-1.5 rounded-full bg-[#f7ce86] shadow-glow-cyan flex-shrink-0" />}
            </>
          )}
        </Link>
      );
    })()}

    {/* Grouped nav items */}
    {navGroups.groups.map(group => {
      const isExpanded = expandedGroups.has(group.label);
      const hasActiveItem = group.items.some(item => item.path === location.pathname);

      return (
        <div key={group.label}>
          {/* Group header */}
          {collapsed ? (
            <div className="relative group py-2 flex justify-center" title={group.label}>
              <span className={`text-[#9e8b66] ${hasActiveItem ? 'text-[#5b4824]' : ''}`}>{group.icon}</span>
            </div>
          ) : (
            <button
              onClick={() => toggleGroup(group.label)}
              className="w-full flex items-center gap-2 px-3 py-2 mt-2 text-xs font-semibold uppercase tracking-[0.08em] text-[#b5a382] hover:text-[#7a6b4e] transition-colors"
            >
              <span>{group.icon}</span>
              <span>{group.label}</span>
              <svg
                className={`w-3.5 h-3.5 ml-auto transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`}
                fill="none" stroke="currentColor" viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
          )}

          {/* Group items */}
          {(collapsed || isExpanded) && (
            <div className={`space-y-0.5 ${collapsed ? '' : 'ml-2'} overflow-hidden transition-all duration-200`}>
              {group.items.map(item => {
                const isActive = location.pathname === item.path;
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    onClick={() => setMobileOpen(false)}
                    title={collapsed ? item.label : undefined}
                    className={`nav-item flex items-center rounded-xl text-sm font-semibold transition-all duration-200 ${
                      collapsed ? 'justify-center px-0 py-3' : 'gap-3 px-4 py-2.5'
                    } ${isActive ? 'nav-item-active text-[#3a2d14]' : 'text-[#7a6b4e]'}`}
                  >
                    <span className={`flex-shrink-0 ${isActive ? 'text-[#5b4824]' : 'text-[#9e8b66]'}`}>{item.icon}</span>
                    {!collapsed && (
                      <>
                        <span className="truncate">{item.label}</span>
                        {isActive && <div className="ml-auto w-1.5 h-1.5 rounded-full bg-[#f7ce86] shadow-glow-cyan flex-shrink-0" />}
                      </>
                    )}
                  </Link>
                );
              })}
            </div>
          )}
        </div>
      );
    })}
  </div>
</nav>
```

### Step 2.5: Verify build and test manually

Run: `cd frontend && npm run build`
Expected: Build succeeds.

Manual checks:
- Sidebar shows Dashboard standalone + 3 accordion groups
- Groups expand/collapse on click
- Collapsed sidebar shows group icons
- Active page's group auto-expands
- Group state persists in localStorage

### Step 2.6: Commit

```bash
git add frontend/src/components/Layout.tsx
git commit -m "feat: group sidebar navigation into accordion categories"
```

---

## Task 3: Dark Mode

**Files:**
- Modify: `frontend/src/index.css` (lines 4-22 for variables, 28-371 for dark variants)
- Modify: `frontend/tailwind.config.js` (line 2 add darkMode)
- Modify: `frontend/src/components/Layout.tsx` (add theme toggle to topbar)

---

### Step 3.1: Add darkMode config to Tailwind

Modify `frontend/tailwind.config.js:2` — add darkMode before content:

```js
export default {
  darkMode: 'class',
  content: [
```

### Step 3.2: Define dark palette CSS variables

Modify `frontend/src/index.css` — add dark theme variables after the `:root` block (after line 22):

```css
.dark {
  --color-dark-900: #1a1714;
  --color-dark-800: #231f1a;
  --color-dark-700: #2d2820;
  --color-dark-600: #3d362b;
  --color-dark-500: #4d4538;
  --color-dark-400: #8a7d65;
  --color-dark-300: #c4b89a;

  --color-accent-primary: #f7ce86;
  --color-accent-secondary: #5b4824;
  --color-accent-tertiary: #3d4a2e;

  --surface-base: rgba(26, 23, 20, 0.96);
  --surface-raised: rgba(45, 40, 32, 0.98);
  --surface-border: rgba(247, 206, 134, 0.12);
  --surface-border-strong: rgba(247, 206, 134, 0.25);
  --shadow-strong: 0 20px 60px rgba(0, 0, 0, 0.3);
}
```

### Step 3.3: Add dark variants to body and global styles

After the `.dark` variables block, add:

```css
.dark body,
body:is(.dark *) {
  background: #1a1714;
  color: #c4b89a;
}

.dark body::before {
  background-image:
    linear-gradient(rgba(247, 206, 134, 0.02) 1px, transparent 1px),
    linear-gradient(90deg, rgba(247, 206, 134, 0.02) 1px, transparent 1px);
}

.dark ::-webkit-scrollbar-track {
  background: rgba(45, 40, 32, 0.75);
}

.dark ::-webkit-scrollbar-thumb {
  background: linear-gradient(180deg, rgba(247, 206, 134, 0.35), rgba(91, 72, 36, 0.6));
  border-color: rgba(45, 40, 32, 0.95);
}

.dark ::selection {
  background: rgba(247, 206, 134, 0.3);
  color: #f5f0e8;
}
```

### Step 3.4: Add dark variants for all component classes

Add after each existing class (or group them at the end before the media query at line 363):

```css
/* --- Dark Mode Component Overrides --- */

.dark .glass-effect {
  background: rgba(26, 23, 20, 0.88);
  backdrop-filter: blur(16px);
}

.dark .card-dark {
  background: #2d2820;
  border-color: var(--surface-border);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
}
.dark .card-dark:hover {
  border-color: var(--surface-border-strong);
  box-shadow: 0 8px 28px rgba(0, 0, 0, 0.3);
}

.dark .btn-primary {
  background: #f7ce86;
  color: #1a1714;
}
.dark .btn-primary:hover {
  box-shadow: 0 8px 20px rgba(247, 206, 134, 0.25);
}

.dark .btn-secondary {
  background: rgba(247, 206, 134, 0.1);
  color: #f7ce86;
  border-color: rgba(247, 206, 134, 0.2);
}
.dark .btn-secondary:hover {
  background: rgba(247, 206, 134, 0.18);
  border-color: rgba(247, 206, 134, 0.35);
}

.dark .btn-danger {
  background: rgba(203, 81, 80, 0.15);
  color: #ef7170;
  border-color: rgba(203, 81, 80, 0.3);
}
.dark .btn-danger:hover {
  background: rgba(203, 81, 80, 0.25);
}

.dark .input-dark {
  background: #231f1a;
  border-color: #3d362b;
  color: #f5f0e8;
}
.dark .input-dark:focus {
  border-color: #f7ce86;
  box-shadow: 0 0 0 3px rgba(247, 206, 134, 0.15);
}
.dark .input-dark::placeholder {
  color: #8a7d65;
}

.dark .badge-success {
  background: rgba(34, 197, 94, 0.15);
  color: #4ade80;
  border-color: rgba(34, 197, 94, 0.3);
}
.dark .badge-warning {
  background: rgba(245, 158, 11, 0.15);
  color: #fbbf24;
  border-color: rgba(245, 158, 11, 0.3);
}
.dark .badge-danger {
  background: rgba(203, 81, 80, 0.15);
  color: #ef7170;
  border-color: rgba(203, 81, 80, 0.3);
}
.dark .badge-info {
  background: rgba(247, 206, 134, 0.1);
  color: #f7ce86;
  border-color: rgba(247, 206, 134, 0.2);
}
.dark .badge-neutral {
  background: rgba(138, 125, 101, 0.15);
  color: #8a7d65;
  border-color: rgba(138, 125, 101, 0.25);
}

.dark .stat-card {
  background: #2d2820;
  border-color: var(--surface-border);
}

.dark .table-dark th {
  background: rgba(61, 54, 43, 0.6);
  color: #c4b89a;
  border-bottom-color: rgba(247, 206, 134, 0.12);
}
.dark .table-dark td {
  color: #f5f0e8;
  border-bottom-color: rgba(247, 206, 134, 0.06);
}
.dark .table-dark tr:hover td {
  background: rgba(247, 206, 134, 0.06);
}

.dark .sidebar-surface {
  background: #231f1a;
  border-right-color: rgba(247, 206, 134, 0.08);
}

.dark .topbar-surface {
  background: rgba(26, 23, 20, 0.88);
  backdrop-filter: blur(14px);
  border-bottom-color: rgba(247, 206, 134, 0.08);
}

.dark .brand-mark {
  background: linear-gradient(130deg, #f7ce86 0%, #8a6d35 100%);
}

.dark .nav-item:hover {
  border-color: rgba(247, 206, 134, 0.15);
  background: rgba(247, 206, 134, 0.08);
}

.dark .nav-item-active {
  border-color: rgba(247, 206, 134, 0.25);
  background: linear-gradient(90deg, rgba(247, 206, 134, 0.12), rgba(61, 74, 46, 0.1));
  box-shadow: inset 0 0 0 1px rgba(247, 206, 134, 0.15);
}
```

### Step 3.5: Build theme toggle into Layout topbar

Modify `frontend/src/components/Layout.tsx` — add theme state and toggle.

Add after the `collapsed` state/effect block (after line 19):

```tsx
const [theme, setTheme] = useState<'light' | 'dark'>(() => {
  try {
    const saved = localStorage.getItem('mp_theme');
    if (saved === 'dark' || saved === 'light') return saved;
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  } catch { return 'light'; }
});

useEffect(() => {
  document.documentElement.classList.toggle('dark', theme === 'dark');
  try { localStorage.setItem('mp_theme', theme); } catch {}
}, [theme]);
```

Add the toggle button in the topbar header (inside the `<div className="hidden sm:flex items-center gap-3">` at line 210), before the "Live analytics" badge:

```tsx
<button
  onClick={() => setTheme(t => t === 'light' ? 'dark' : 'light')}
  className="p-2 rounded-lg text-[#9e8b66] hover:text-[#5b4824] hover:bg-[#5b4824]/10 transition-colors"
  title={theme === 'light' ? 'Dark mode' : 'Light mode'}
>
  {theme === 'light' ? (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
    </svg>
  ) : (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
    </svg>
  )}
</button>
```

### Step 3.6: Update hardcoded colors in Layout.tsx

Many colors in Layout.tsx are hardcoded (e.g., `text-[#3a2d14]`, `bg-[#5b4824]/10`). These need dark-aware equivalents. The simplest approach: add `dark:` prefixed classes where hardcoded colors appear.

Key updates in Layout.tsx:
- Line 94: `text-[#5f471d]` → add `dark:text-[#c4b89a]`
- Line 117: `text-[#3a2d14]` → add `dark:text-[#f5f0e8]`
- Line 118: `text-[#9e8b66]` → add `dark:text-[#8a7d65]`
- Line 145: `text-[#3a2d14]` → add `dark:text-[#f5f0e8]`
- Line 145: `text-[#7a6b4e]` → add `dark:text-[#8a7d65]`
- Line 147: `text-[#5b4824]` / `text-[#9e8b66]` → add dark variants
- Line 206: `text-[#3a2d14]` → add `dark:text-[#f5f0e8]`
- Line 205: `text-[#b5a382]` → add `dark:text-[#8a7d65]`

### Step 3.7: Verify build

Run: `cd frontend && npm run build`
Expected: Build succeeds.

### Step 3.8: Commit

```bash
git add frontend/src/index.css frontend/tailwind.config.js frontend/src/components/Layout.tsx
git commit -m "feat: add dark mode with CSS variables and theme toggle"
```

---

## Task 4: Dashboard Enhancement (Trends + Sparklines)

**Files:**
- Create: `frontend/src/components/Sparkline.tsx`
- Modify: `frontend/src/pages/Dashboard.tsx`
- Modify: `frontend/src/services/api.ts` (add trend endpoint)
- Modify: `backend/app/api/routes.py` (add trend endpoint)

---

### Step 4.1: Add backend trend stats endpoint

Modify `backend/app/api/routes.py` — add after the existing `/stats` endpoint (after line 811):

```python
@router.get("/stats/trends")
async def get_stats_trends(db: Session = Depends(get_db)):
    """Return daily counts for the last 7 days for sparkline charts."""
    from datetime import datetime, timedelta
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=6)

    # Products created per day
    product_counts = (
        db.query(
            func.date(Product.created_at).label("day"),
            func.count(Product.id).label("count"),
        )
        .filter(func.date(Product.created_at) >= start_date)
        .group_by(func.date(Product.created_at))
        .order_by(func.date(Product.created_at))
        .all()
    )

    # Snapshots per day
    snapshot_counts = (
        db.query(
            ProductSnapshot.snapshot_date,
            func.count(ProductSnapshot.id).label("count"),
        )
        .filter(ProductSnapshot.snapshot_date >= start_date)
        .group_by(ProductSnapshot.snapshot_date)
        .order_by(ProductSnapshot.snapshot_date)
        .all()
    )

    # Tasks per day
    task_counts = (
        db.query(
            func.date(SearchTask.created_at).label("day"),
            func.count(SearchTask.id).label("count"),
        )
        .filter(func.date(SearchTask.created_at) >= start_date)
        .group_by(func.date(SearchTask.created_at))
        .order_by(func.date(SearchTask.created_at))
        .all()
    )

    # Completed tasks per day
    completed_counts = (
        db.query(
            func.date(SearchTask.created_at).label("day"),
            func.count(SearchTask.id).label("count"),
        )
        .filter(
            func.date(SearchTask.created_at) >= start_date,
            SearchTask.status == "completed",
        )
        .group_by(func.date(SearchTask.created_at))
        .order_by(func.date(SearchTask.created_at))
        .all()
    )

    def to_series(rows):
        day_map = {str(r[0]): r[1] for r in rows}
        return [
            day_map.get(str(start_date + timedelta(days=i)), 0)
            for i in range(7)
        ]

    return {
        "products": to_series(product_counts),
        "snapshots": to_series(snapshot_counts),
        "tasks": to_series(task_counts),
        "completed": to_series(completed_counts),
    }
```

**Note:** Make sure `from sqlalchemy import func` is imported at top of routes.py (check existing imports).

### Step 4.2: Add frontend API call for trends

Modify `frontend/src/services/api.ts` — add after the `getStats` function (after line ~206):

```typescript
export interface StatTrends {
  products: number[];
  snapshots: number[];
  tasks: number[];
  completed: number[];
}

export const getStatTrends = async (): Promise<StatTrends> => {
  const cacheKey = buildCacheKey(CACHE_PREFIX.stats, 'trends');
  return getCachedOrFetch(cacheKey, async () => {
    const response = await api.get('/stats/trends');
    return response.data;
  });
};
```

### Step 4.3: Create Sparkline SVG component

Create `frontend/src/components/Sparkline.tsx`:

```tsx
interface SparklineProps {
  data: number[];
  color: string;
  width?: number;
  height?: number;
}

export default function Sparkline({ data, color, width = 100, height = 28 }: SparklineProps) {
  if (!data.length || data.every(v => v === 0)) return null;

  const max = Math.max(...data, 1);
  const min = Math.min(...data, 0);
  const range = max - min || 1;

  const points = data.map((value, i) => {
    const x = (i / (data.length - 1)) * width;
    const y = height - ((value - min) / range) * (height - 4) - 2;
    return `${x},${y}`;
  });

  const linePath = `M${points.join(' L')}`;
  const areaPath = `${linePath} L${width},${height} L0,${height} Z`;

  return (
    <svg width={width} height={height} className="overflow-visible">
      <defs>
        <linearGradient id={`sparkGrad-${color.replace('#', '')}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity={0.2} />
          <stop offset="100%" stopColor={color} stopOpacity={0} />
        </linearGradient>
      </defs>
      <path d={areaPath} fill={`url(#sparkGrad-${color.replace('#', '')})`} />
      <path d={linePath} fill="none" stroke={color} strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function TrendIndicator({ data }: { data: number[] }) {
  if (data.length < 2) return null;

  const recent = data.slice(-3).reduce((a, b) => a + b, 0);
  const older = data.slice(0, 3).reduce((a, b) => a + b, 0);
  if (older === 0 && recent === 0) return null;

  const change = older === 0 ? 100 : ((recent - older) / older) * 100;
  const isUp = change > 0;
  const isFlat = Math.abs(change) < 1;

  if (isFlat) {
    return <span className="text-xs text-[#9e8b66]">--</span>;
  }

  return (
    <span className={`text-xs font-semibold flex items-center gap-0.5 ${isUp ? 'text-success' : 'text-danger'}`}>
      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5}
          d={isUp ? 'M5 15l7-7 7 7' : 'M19 9l-7 7-7-7'} />
      </svg>
      {Math.abs(change).toFixed(0)}%
    </span>
  );
}
```

### Step 4.4: Update Dashboard.tsx with sparklines and trends

Modify `frontend/src/pages/Dashboard.tsx`:

**Update imports (line 2):**
```tsx
import { createSearchTask, getSearchTask, getTasks, getStats, getStatTrends } from '../services/api';
import type { SearchTask, Stats, StatTrends } from '../services/api';
```

**Add trends state (after line 11):**
```tsx
const [trends, setTrends] = useState<StatTrends | null>(null);
```

**Update loadData (line 33) to also fetch trends:**
```tsx
const [tasksData, statsData, trendsData] = await Promise.all([
  getTasks(10),
  getStats(),
  getStatTrends().catch(() => null),
]);
setTasks(tasksData);
setStats(statsData);
setTrends(trendsData);
```

**Add Sparkline imports (line 1 area):**
```tsx
import Sparkline, { TrendIndicator } from '../components/Sparkline';
```

**Update statCards definition (lines 71-92) to include trend data:**
```tsx
const trendKeys: (keyof StatTrends)[] = ['products', 'snapshots', 'tasks', 'completed'];
const statCards = [
  { label: 'Total Products', value: stats?.total_products || 0, color: '#1e9df1', trendKey: 'products' as const, icon: /* existing */ },
  { label: 'Data Points', value: stats?.total_snapshots || 0, color: '#22c55e', trendKey: 'snapshots' as const, icon: /* existing */ },
  { label: 'Total Searches', value: stats?.total_tasks || 0, color: '#f7b928', trendKey: 'tasks' as const, icon: /* existing */ },
  { label: 'Completed', value: stats?.completed_tasks || 0, color: '#f59e0b', trendKey: 'completed' as const, icon: /* existing */ },
];
```

**Update stat card rendering (lines 164-184) — add sparkline and trend:**
```tsx
<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4">
  {statCards.map((stat, index) => (
    <div
      key={index}
      className="stat-card"
      style={{ '--stat-color': stat.color } as React.CSSProperties}
    >
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <div className="text-2xl md:text-3xl font-bold text-[#0f1419] dark:text-[#f5f0e8] mb-1" style={{ color: stat.color }}>
              {stat.value.toLocaleString()}
            </div>
            {trends && <TrendIndicator data={trends[stat.trendKey]} />}
          </div>
          <div className="text-xs md:text-sm text-[#9e8b66]">{stat.label}</div>
        </div>
        <div className="p-2 rounded-lg" style={{ backgroundColor: `${stat.color}15` }}>
          <span style={{ color: stat.color }}>{stat.icon}</span>
        </div>
      </div>
      {trends && (
        <div className="mt-3">
          <Sparkline data={trends[stat.trendKey]} color={stat.color} />
        </div>
      )}
    </div>
  ))}
</div>
```

### Step 4.5: Verify build

Run: `cd frontend && npm run build`
Expected: Build succeeds.

### Step 4.6: Commit

```bash
git add frontend/src/components/Sparkline.tsx frontend/src/pages/Dashboard.tsx frontend/src/services/api.ts backend/app/api/routes.py
git commit -m "feat: add dashboard sparklines and trend indicators"
```

---

## Task 5: Component Decomposition (PriceMonitor + CategoryExplorer)

> This is the largest task. Each sub-component follows extract-and-replace pattern.

**Files:**
- Create: `frontend/src/hooks/usePriceMonitor.ts`
- Create: `frontend/src/components/price-monitor/PriceMonitorFilters.tsx`
- Create: `frontend/src/components/price-monitor/MonitoredProductList.tsx`
- Create: `frontend/src/components/price-monitor/FetchTaskProgress.tsx`
- Modify: `frontend/src/pages/PriceMonitor.tsx` (reduce from 1010 → ~120 lines)
- Create: `frontend/src/hooks/useCategoryExplorer.ts`
- Create: `frontend/src/components/category-explorer/CategoryTree.tsx`
- Create: `frontend/src/components/category-explorer/CategoryFilters.tsx`
- Create: `frontend/src/components/category-explorer/CategoryResultsTable.tsx`
- Modify: `frontend/src/pages/CategoryExplorer.tsx` (reduce from 1584 → ~150 lines)

---

### Step 5.1: Extract PriceMonitor state into useReducer + custom hook

Create `frontend/src/hooks/usePriceMonitor.ts`:

**State shape (replacing 28 useState + 5 refs):**

```tsx
import { useReducer, useCallback, useEffect, useRef } from 'react';
import type { MonitoredProduct, SellerSnapshot } from '../services/api';

interface PriceMonitorState {
  platform: 'hepsiburada' | 'trendyol';
  products: MonitoredProduct[];
  selectedProduct: MonitoredProduct | null;
  sellers: SellerSnapshot[];
  loading: boolean;
  sellersLoading: boolean;
  brands: string[];
  // Filters
  selectedBrand: string;
  priceAlertOnly: boolean;
  campaignAlertOnly: boolean;
  searchInput: string;
  searchQuery: string;
  showInactive: boolean;
  currentOffset: number;
  // Fetch state
  fetchTaskId: string | null;
  fetchStatus: string;
  fetchProgress: { completed: number; total: number } | null;
  currentFetchType: string | null;
  // Counts
  totalProducts: number;
  activeTotalCount: number;
  inactiveTotalCount: number;
  lastInactiveCount: number;
  // UI toggles
  showFetchMenu: boolean;
  showExportMenu: boolean;
  showImportModal: boolean;
  showDeleteModal: 'all' | 'inactive' | null;
  importJson: string;
  importLoading: boolean;
  exportLoading: boolean;
  deleteLoading: boolean;
}

type PriceMonitorAction =
  | { type: 'SET_PLATFORM'; payload: 'hepsiburada' | 'trendyol' }
  | { type: 'SET_PRODUCTS'; payload: { products: MonitoredProduct[]; total: number; activeTotal: number; inactiveTotal: number } }
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_SELECTED_PRODUCT'; payload: MonitoredProduct | null }
  | { type: 'SET_SELLERS'; payload: { sellers: SellerSnapshot[]; loading: boolean } }
  | { type: 'SET_FILTER'; payload: Partial<Pick<PriceMonitorState, 'selectedBrand' | 'priceAlertOnly' | 'campaignAlertOnly' | 'searchInput' | 'searchQuery' | 'showInactive' | 'currentOffset'>> }
  | { type: 'SET_FETCH'; payload: Partial<Pick<PriceMonitorState, 'fetchTaskId' | 'fetchStatus' | 'fetchProgress' | 'currentFetchType'>> }
  | { type: 'SET_UI'; payload: Partial<Pick<PriceMonitorState, 'showFetchMenu' | 'showExportMenu' | 'showImportModal' | 'showDeleteModal' | 'importJson' | 'importLoading' | 'exportLoading' | 'deleteLoading'>> }
  | { type: 'SET_BRANDS'; payload: string[] }
  | { type: 'SET_LAST_INACTIVE_COUNT'; payload: number };

function reducer(state: PriceMonitorState, action: PriceMonitorAction): PriceMonitorState {
  switch (action.type) {
    case 'SET_PLATFORM':
      return { ...state, platform: action.payload, products: [], selectedProduct: null, sellers: [], currentOffset: 0 };
    case 'SET_PRODUCTS':
      return { ...state, products: action.payload.products, totalProducts: action.payload.total, activeTotalCount: action.payload.activeTotal, inactiveTotalCount: action.payload.inactiveTotal, loading: false };
    case 'SET_LOADING':
      return { ...state, loading: action.payload };
    case 'SET_SELECTED_PRODUCT':
      return { ...state, selectedProduct: action.payload };
    case 'SET_SELLERS':
      return { ...state, sellers: action.payload.sellers, sellersLoading: action.payload.loading };
    case 'SET_FILTER':
      return { ...state, ...action.payload };
    case 'SET_FETCH':
      return { ...state, ...action.payload };
    case 'SET_UI':
      return { ...state, ...action.payload };
    case 'SET_BRANDS':
      return { ...state, brands: action.payload };
    case 'SET_LAST_INACTIVE_COUNT':
      return { ...state, lastInactiveCount: action.payload };
    default:
      return state;
  }
}

export function usePriceMonitor() {
  const [state, dispatch] = useReducer(reducer, {
    platform: 'hepsiburada',
    products: [],
    selectedProduct: null,
    sellers: [],
    loading: false,
    sellersLoading: false,
    brands: [],
    selectedBrand: '',
    priceAlertOnly: false,
    campaignAlertOnly: false,
    searchInput: '',
    searchQuery: '',
    showInactive: false,
    currentOffset: 0,
    fetchTaskId: null,
    fetchStatus: '',
    fetchProgress: null,
    currentFetchType: null,
    totalProducts: 0,
    activeTotalCount: 0,
    inactiveTotalCount: 0,
    lastInactiveCount: 0,
    showFetchMenu: false,
    showExportMenu: false,
    showImportModal: false,
    showDeleteModal: null,
    importJson: '',
    importLoading: false,
    exportLoading: false,
    deleteLoading: false,
  });

  // Move all existing useEffect hooks and handler functions here
  // Each handler calls dispatch() instead of individual setters
  // Return { state, dispatch, handlers }

  return { state, dispatch };
}
```

> **Implementation note:** The implementer should move ALL the useEffect, callback, and handler functions from `PriceMonitor.tsx` (lines 69-380) into this hook, replacing each `setState` call with the appropriate `dispatch({ type: ... })`. This is a mechanical refactor — logic stays the same, only state access changes.

### Step 5.2: Extract PriceMonitor sub-components

Create the sub-component files. Each receives state and dispatch (or specific handler callbacks) as props. The implementer should:

1. **`PriceMonitorFilters.tsx`**: Extract the filter bar section from PriceMonitor.tsx (lines ~385-530) — platform tabs, brand filter, search input, alert toggles, action buttons
2. **`MonitoredProductList.tsx`**: Extract the product list section (lines ~531-749) — product cards with pagination
3. **`FetchTaskProgress.tsx`**: Extract the fetch progress section (lines ~440-530) — progress bar, status display

### Step 5.3: Rewrite PriceMonitor.tsx as orchestrator

The page component becomes a thin orchestrator (~120 lines):

```tsx
import { usePriceMonitor } from '../hooks/usePriceMonitor';
import PriceMonitorFilters from '../components/price-monitor/PriceMonitorFilters';
import MonitoredProductList from '../components/price-monitor/MonitoredProductList';
import FetchTaskProgress from '../components/price-monitor/FetchTaskProgress';

export default function PriceMonitor() {
  const { state, dispatch } = usePriceMonitor();

  return (
    <div className="space-y-5 animate-fade-in">
      <PriceMonitorFilters state={state} dispatch={dispatch} />
      {state.fetchTaskId && <FetchTaskProgress state={state} />}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <MonitoredProductList state={state} dispatch={dispatch} />
        </div>
        {/* Seller detail panel */}
      </div>
    </div>
  );
}
```

### Step 5.4: Verify build after PriceMonitor decomposition

Run: `cd frontend && npm run build`
Expected: Build succeeds. PriceMonitor page behaves identically to before.

### Step 5.5: Commit PriceMonitor decomposition

```bash
git add frontend/src/hooks/usePriceMonitor.ts frontend/src/components/price-monitor/ frontend/src/pages/PriceMonitor.tsx
git commit -m "refactor: decompose PriceMonitor into hook + sub-components"
```

### Step 5.6: Extract CategoryExplorer state into useReducer + custom hook

Same pattern as PriceMonitor. Create `frontend/src/hooks/useCategoryExplorer.ts`:

**State shape (replacing 28 useState):**

```tsx
interface CategoryExplorerState {
  platform: '' | 'hepsiburada' | 'trendyol' | 'web';
  viewMode: 'my_products' | 'category_page';
  // My products data
  data: StoreProductListResponse | null;
  filters: StoreProductFilters | null;
  categoryTree: CategoryTreeNode[];
  // Category page data
  catData: CategoryProductListResponse | null;
  catFilterData: CategoryFilterData | null;
  // My products filters
  search: string;
  selectedCategory: string;
  selectedBrand: string;
  minPrice: string;
  maxPrice: string;
  minRating: string;
  sortBy: string;
  sortDir: string;
  page: number;
  pageSize: number;
  // Category page filters
  catBrand: string;
  catSeller: string;
  catMinPrice: string;
  catMaxPrice: string;
  catMinRating: string;
  catSponsored: '' | 'true' | 'false';
  catSortBy: string;
  catSortDir: string;
  // Product selection
  selectedProduct: StoreProduct | null;
  selectedCatProduct: CategoryProductItem | null;
  expandedCategories: Set<string>;
  // Scraping
  showScraper: boolean;
  scrapeUrl: string;
  scrapePageCount: number;
  scraping: boolean;
  scrapeMsg: string;
  scrapeProgress: string;
  scrapeSessionId: string;
  // UI
  loading: boolean;
  showMobileFilters: boolean;
  showDetailPanel: boolean;
  selectedForDetail: Set<number>;
  detailFetching: boolean;
  detailProgress: string;
}
```

> Same mechanical refactor: move useEffects and handlers into hook, replace setState with dispatch.

### Step 5.7: Extract CategoryExplorer sub-components

Create sub-component files:

1. **`CategoryTree.tsx`**: Tree navigation with expand/collapse (from lines ~470-507)
2. **`CategoryFilters.tsx`**: Filter panels for both view modes (from lines ~600+)
3. **`CategoryResultsTable.tsx`**: Product cards/table for both view modes (from lines ~509-800+)

### Step 5.8: Rewrite CategoryExplorer.tsx as orchestrator

Same thin orchestrator pattern as PriceMonitor.

### Step 5.9: Verify build after CategoryExplorer decomposition

Run: `cd frontend && npm run build`
Expected: Build succeeds.

### Step 5.10: Commit CategoryExplorer decomposition

```bash
git add frontend/src/hooks/useCategoryExplorer.ts frontend/src/components/category-explorer/ frontend/src/pages/CategoryExplorer.tsx
git commit -m "refactor: decompose CategoryExplorer into hook + sub-components"
```

---

## Summary: Execution Order

```
Task 1: Skeleton Loading     [no deps]        ~30 min
Task 2: Navigation Grouping  [no deps]        ~45 min
Task 3: Dark Mode            [no deps]        ~90 min
Task 4: Dashboard Sparklines [after Task 1]   ~45 min
Task 5: Component Decomp     [after Task 1,3] ~3-4 hours
```

**Tasks 1, 2, and 3 can run in parallel.**
**Task 4 depends on Task 1 (skeleton for dashboard).**
**Task 5 depends on Tasks 1 and 3 (skeleton + dark classes settled).**
