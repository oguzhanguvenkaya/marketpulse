# MarketPulse UI/UX Improvements Design

> Date: 2026-02-23
> Status: Approved
> Scope: 5 work packages, ~15 subtasks

---

## Context

MarketPulse is a marketplace data analysis platform with a React 19 + TypeScript + Tailwind CSS v4 frontend. A comprehensive UI/UX audit identified the following high-impact improvement areas:

- **Navigation:** 12 flat sidebar items create cognitive overload
- **Loading UX:** Spinner-only loading states feel unpolished
- **Theming:** No dark mode support for a data-heavy tool used for long sessions
- **Dashboard:** Minimal dashboard with no trend visualization
- **Component complexity:** PriceMonitor (1010 lines, 31 useState) and CategoryExplorer (1584 lines, 42 useState) are unmaintainable monoliths

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Dark mode approach | CSS custom properties + class toggle | Existing CSS variables make migration easy. User control via toggle + prefers-color-scheme fallback |
| Dashboard enhancement | Trend cards + sparklines | Adds value without full redesign. Leverages existing Plotly.js |
| Navigation structure | Accordion groups | 4 groups (Dashboard, Pazaryerleri, Analiz, Araclar). Reduces cognitive load while preserving access |
| Skeleton approach | Custom primitives | No library dependency. Matches existing warm design tokens |
| Component refactoring | Custom hooks + sub-components | useReducer for state groups, extract logical UI sections |

---

## Task 1: Navigation Grouping (Accordion Sidebar)

**Files:** `frontend/src/components/Layout.tsx`
**Dependency:** None

### Design

Current flat navigation (12 items) reorganized into accordion groups:

```
Dashboard (always visible, no group)
---
Pazaryerleri (collapsible)
  - Hepsiburada
  - Trendyol
  - Web Products
---
Analiz (collapsible)
  - Products
  - Ads
  - Price Monitor
  - Sellers
  - Categories
---
Araclar (collapsible)
  - URL Scraper
  - Transcripts
  - JSON Editor
```

### Behavior
- Groups persist open/closed state in localStorage (`mp_nav_groups`)
- Active page's group auto-expands
- Collapsed sidebar: show group icon, tooltip on hover
- Smooth expand/collapse animation (200ms ease)
- Chevron rotation indicator

### Subtasks
- 1.1: Refactor nav data structure to nested groups
- 1.2: Implement accordion component with localStorage persistence
- 1.3: Handle collapsed sidebar mode (group icons + tooltips)

---

## Task 2: Skeleton Loading System

**Files:** New `frontend/src/components/Skeleton.tsx`, all page components
**Dependency:** None

### Design

Replace spinner-based `PageLoader` with content-shaped skeleton placeholders.

### Primitives
- `SkeletonLine` - text placeholder (configurable width, height)
- `SkeletonCard` - card placeholder with header + body lines
- `SkeletonTable` - table with header row + N body rows
- `SkeletonChart` - rectangular chart area placeholder
- `SkeletonStatCard` - stat card with number + label

### Styling
- Background: `bg-dark-600/30` (light mode), `bg-dark-300/20` (dark mode)
- Animation: shimmer effect (left-to-right gradient sweep, 1.5s infinite)
- Border radius: matches target component (14px for cards, 8px for lines)

### Page-specific skeletons
- Dashboard: 4 stat cards + search bar + recent list
- Products/Sellers: filter bar + table rows
- PriceMonitor: filter panel + product grid
- ProductDetail: image + info panel + chart area

### Subtasks
- 2.1: Create Skeleton primitive components
- 2.2: Create page-specific skeleton compositions
- 2.3: Replace PageLoader with Skeleton in Suspense fallbacks

---

## Task 3: Dark Mode

**Files:** `frontend/src/index.css`, `frontend/tailwind.config.js`, `frontend/src/components/Layout.tsx`, all components with custom CSS classes
**Dependency:** None (parallel with Task 1 and 2)

### Design

CSS custom properties toggled via `<html class="dark">`.

### Dark Palette
| Token | Light | Dark |
|-------|-------|------|
| --bg-primary | #fffbef | #1a1714 |
| --bg-secondary | #fefbf0 | #231f1a |
| --bg-tertiary | #f7eede | #2d2820 |
| --surface-border | rgba(91,72,36,0.15) | rgba(247,206,134,0.12) |
| --text-primary | #0f1419 | #f5f0e8 |
| --text-secondary | #5f471d | #c4b89a |
| --text-tertiary | #9e8b66 | #8a7d65 |
| --accent-primary | #5b4824 | #f7ce86 |
| --accent-secondary | #f7ce86 | #5b4824 |

### Custom classes to update
All classes in index.css need `.dark` variants:
- `.card-dark` - dark bg, lighter border
- `.input-dark` - dark bg, light text
- `.btn-primary` - inverted (gold bg, dark text)
- `.btn-secondary` - adjusted opacity
- `.badge-*` - adjusted backgrounds
- `.table-dark` - dark rows, lighter headers
- `.stat-card` - dark surface
- `.glass-effect` - dark glass
- `.sidebar-surface`, `.topbar-surface` - dark surfaces
- `.nav-item`, `.nav-item-active` - adjusted colors
- Scrollbar, selection colors

### Theme Toggle
- Sun/moon icon button in topbar (right side)
- localStorage key: `mp_theme` ("light" | "dark")
- On load: check localStorage, fallback to `prefers-color-scheme`
- Smooth transition: `transition: background-color 0.3s, color 0.3s` on root

### Plotly Charts
- Dark mode layout: dark paper/plot bg, light grid lines, light text
- Responsive to theme changes

### Subtasks
- 3.1: Define dark palette CSS variables under `.dark` selector
- 3.2: Configure `darkMode: 'class'` in tailwind.config.js
- 3.3: Update all custom CSS classes with dark variants
- 3.4: Build theme toggle component + persistence logic
- 3.5: Adapt Plotly chart themes for dark mode

---

## Task 4: Dashboard Enhancement (Trends + Sparklines)

**Files:** `frontend/src/pages/Dashboard.tsx`
**Dependency:** Task 2 (skeleton loading for dashboard)

### Design

Enhance existing stat cards with trend data and add activity timeline.

### Stat Card Enhancement
Current: Large number + label
New: Large number + label + sparkline (7-day mini chart) + trend arrow (up/down %)

```
┌─────────────────────────────┐
│  [icon]                     │
│  1,247          ↑ 12.3%     │
│  Total Products             │
│  ▁▂▃▂▄▅▆ (sparkline)       │
└─────────────────────────────┘
```

### Sparkline Implementation
- Inline SVG (not Plotly - too heavy for mini charts)
- 7 data points, line + area fill
- Color matches stat card theme color
- No axes, no labels - pure visualization

### Trend Indicator
- Green up arrow + positive %: growth
- Red down arrow + negative %: decline
- Gray dash: no change
- Compared to previous 7-day period

### Activity Timeline
- "Son Aktivite" section below stat cards
- Shows: last 5 events (scrapes, price changes, alerts)
- Each entry: icon + description + relative time ("2 saat once")
- Color-coded by type (green: success, amber: warning, red: alert)

### Backend Support
- New endpoint: `GET /api/stats/trends` returning 7-day stat history
- Reuses existing snapshot/task data

### Subtasks
- 4.1: Add sparkline SVG component + stat card trend indicators
- 4.2: Add trend percentage calculation + up/down arrows
- 4.3: Build activity timeline component with recent events

---

## Task 5: Component Decomposition

**Files:** `frontend/src/pages/PriceMonitor.tsx`, `frontend/src/pages/CategoryExplorer.tsx`
**Dependency:** Task 2 (skeleton), Task 3 (dark mode classes settled)

### PriceMonitor Decomposition (1010 lines, 31 useState)

**New structure:**
```
pages/PriceMonitor.tsx (orchestrator, ~100 lines)
hooks/usePriceMonitor.ts (state + logic, ~300 lines)
components/price-monitor/
  PriceMonitorFilters.tsx (~150 lines)
  MonitoredProductList.tsx (~200 lines)
  ProductMonitorCard.tsx (~100 lines)
  FetchTaskHistory.tsx (~150 lines)
```

**State grouping (useReducer):**
```typescript
interface PriceMonitorState {
  filters: { brand: string; alertType: string; sortBy: string; search: string }
  products: { items: Product[]; loading: boolean; error: string | null }
  tasks: { items: Task[]; activeTask: Task | null }
  ui: { selectedProducts: Set<string>; expandedProduct: string | null }
}
```

### CategoryExplorer Decomposition (1584 lines, 42 useState)

**New structure:**
```
pages/CategoryExplorer.tsx (orchestrator, ~120 lines)
hooks/useCategoryExplorer.ts (state + logic, ~400 lines)
components/category-explorer/
  CategoryTree.tsx (~200 lines)
  CategoryFilters.tsx (~150 lines)
  CategoryResultsTable.tsx (~250 lines)
  CategoryStats.tsx (~100 lines)
  CategoryScrapeModal.tsx (~150 lines)
```

**State grouping (useReducer):**
```typescript
interface CategoryExplorerState {
  tree: { nodes: TreeNode[]; expanded: Set<string>; selected: string | null }
  filters: { platform: string; sortBy: string; search: string; priceRange: [number, number] }
  results: { items: Product[]; loading: boolean; pagination: Pagination }
  scraping: { active: boolean; progress: number; modal: boolean }
  ui: { viewMode: string; selectedItems: Set<string> }
}
```

### Subtasks
- 5.1: Extract PriceMonitor into hook + sub-components
- 5.2: Extract CategoryExplorer into hook + sub-components
- 5.3: Convert grouped useState to useReducer

---

## Implementation Order

```
Phase 1 (Parallel):
  Task 1: Navigation Grouping
  Task 2: Skeleton Loading
  Task 3: Dark Mode (3.1-3.3 first, then 3.4-3.5)

Phase 2 (Sequential, after Phase 1):
  Task 4: Dashboard Enhancement (needs Task 2 skeletons)

Phase 3 (Sequential, after Phase 1):
  Task 5: Component Decomposition (needs Task 2 skeletons + Task 3 dark classes)
```

---

## Out of Scope

- Toast/notification system (already in existing dev plan 4.4)
- Accessibility improvements (deferred to separate phase)
- Global search feature
- Keyboard shortcuts
- Mobile card view for tables
