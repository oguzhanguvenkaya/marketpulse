// Skeleton loading primitives and page-specific compositions

// Internal shimmer wrapper - not exported
function Shimmer() {
  return (
    <div className="absolute inset-0 -translate-x-full animate-[shimmer_1.5s_infinite] bg-gradient-to-r from-transparent via-white/20 to-transparent" />
  )
}

// ---------- Primitives ----------

export function SkeletonLine({
  width = 'w-full',
  height = 'h-4',
}: {
  width?: string
  height?: string
}) {
  return (
    <div
      className={`${width} ${height} rounded-lg bg-dark-600/30 overflow-hidden relative`}
    >
      <Shimmer />
    </div>
  )
}

export function SkeletonCircle({ size = 'w-10 h-10' }: { size?: string }) {
  return (
    <div
      className={`${size} rounded-full bg-dark-600/30 overflow-hidden relative`}
    >
      <Shimmer />
    </div>
  )
}

export function SkeletonCard() {
  return (
    <div className="card-dark p-5 space-y-4">
      <SkeletonLine width="w-1/3" height="h-5" />
      <div className="space-y-2">
        <SkeletonLine />
        <SkeletonLine width="w-5/6" />
        <SkeletonLine width="w-2/3" />
      </div>
    </div>
  )
}

export function SkeletonStatCard() {
  return (
    <div className="stat-card p-5 flex items-center justify-between">
      <div className="space-y-3 flex-1">
        <SkeletonLine width="w-20" height="h-7" />
        <SkeletonLine width="w-24" height="h-3" />
      </div>
      <SkeletonCircle size="w-11 h-11" />
    </div>
  )
}

export function SkeletonTable({ rows = 5 }: { rows?: number }) {
  return (
    <div className="card-dark overflow-hidden">
      {/* Header row */}
      <div className="flex gap-4 p-4 border-b border-dark-600/20">
        <SkeletonLine width="w-1/4" height="h-4" />
        <SkeletonLine width="w-1/4" height="h-4" />
        <SkeletonLine width="w-1/6" height="h-4" />
        <SkeletonLine width="w-1/6" height="h-4" />
      </div>
      {/* Body rows */}
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className="flex gap-4 p-4 border-b border-dark-600/10 last:border-b-0"
        >
          <SkeletonLine width="w-1/4" height="h-4" />
          <SkeletonLine width="w-1/4" height="h-4" />
          <SkeletonLine width="w-1/6" height="h-4" />
          <SkeletonLine width="w-1/6" height="h-4" />
        </div>
      ))}
    </div>
  )
}

export function SkeletonChart() {
  return (
    <div className="card-dark p-5">
      <SkeletonLine width="w-1/4" height="h-5" />
      <div className="mt-4 w-full h-56 rounded-lg bg-dark-600/30 overflow-hidden relative">
        <Shimmer />
      </div>
    </div>
  )
}

// ---------- Page-specific compositions ----------

export function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      {/* Heading */}
      <SkeletonLine width="w-48" height="h-8" />

      {/* Search card */}
      <div className="card-dark p-5">
        <div className="flex gap-3">
          <SkeletonLine height="h-10" />
          <SkeletonLine width="w-32" height="h-10" />
        </div>
      </div>

      {/* 4 stat cards grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <SkeletonStatCard />
        <SkeletonStatCard />
        <SkeletonStatCard />
        <SkeletonStatCard />
      </div>

      {/* Table with 5 rows */}
      <SkeletonTable rows={5} />
    </div>
  )
}

export function ProductsSkeleton() {
  return (
    <div className="space-y-6">
      {/* Filter bar */}
      <div className="card-dark p-4 flex gap-3">
        <SkeletonLine width="w-48" height="h-10" />
        <SkeletonLine width="w-36" height="h-10" />
        <SkeletonLine width="w-28" height="h-10" />
      </div>

      {/* Table with 8 rows */}
      <SkeletonTable rows={8} />
    </div>
  )
}

export function PriceMonitorSkeleton() {
  return (
    <div className="space-y-6">
      {/* Action buttons */}
      <div className="flex gap-3">
        <SkeletonLine width="w-32" height="h-10" />
        <SkeletonLine width="w-32" height="h-10" />
      </div>

      {/* 2/3 grid: table + card */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <SkeletonTable rows={6} />
        </div>
        <div>
          <SkeletonChart />
        </div>
      </div>
    </div>
  )
}

// ---------- Default export: generic fallback ----------

export default function PageSkeleton() {
  return (
    <div className="space-y-6">
      {/* Heading */}
      <SkeletonLine width="w-48" height="h-8" />

      {/* Card */}
      <SkeletonCard />

      {/* Table */}
      <SkeletonTable />
    </div>
  )
}
