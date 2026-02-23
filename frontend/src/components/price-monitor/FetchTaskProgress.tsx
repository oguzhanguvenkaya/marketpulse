import type { UsePriceMonitorReturn } from '../../hooks/usePriceMonitor';

export default function FetchTaskProgress({
  fetchStatus,
  fetchProgress,
  progressPercent,
}: UsePriceMonitorReturn) {
  if (fetchStatus !== 'running') return null;

  return (
    <div className="p-4 rounded-lg bg-accent-primary/5 border border-accent-primary/20">
      <div className="flex items-center gap-3 text-sm md:text-base">
        <div className="w-2 h-2 rounded-full bg-accent-primary animate-pulse" />
        <span className="text-accent-primary">Fetching prices: {fetchProgress.completed} / {fetchProgress.total} products completed</span>
      </div>
      <div className="mt-2 progress-bar">
        <div className="progress-bar-fill" style={{ width: `${progressPercent}%` }} />
      </div>
    </div>
  );
}
