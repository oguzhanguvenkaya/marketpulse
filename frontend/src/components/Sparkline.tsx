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
    const x = (i / Math.max(data.length - 1, 1)) * width;
    const y = height - ((value - min) / range) * (height - 4) - 2;
    return `${x},${y}`;
  });

  const linePath = `M${points.join(' L')}`;
  const areaPath = `${linePath} L${width},${height} L0,${height} Z`;
  const gradientId = `sparkGrad-${color.replace('#', '')}`;

  return (
    <svg width={width} height={height} className="overflow-visible">
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity={0.2} />
          <stop offset="100%" stopColor={color} stopOpacity={0} />
        </linearGradient>
      </defs>
      <path d={areaPath} fill={`url(#${gradientId})`} />
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
    return <span className="text-xs text-[#9e8b66] dark:text-[#8a7d65]">--</span>;
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
