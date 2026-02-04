import { Skeleton } from '@/components/ui/skeleton';
import { TickerData } from '@/hooks/api/usePriceData';
import { formatNumber } from '@/lib/utils';

interface OverviewStatsProps {
  data?: TickerData;
  isLoading: boolean;
  isConnected: boolean;
}

export function OverviewStats({ data, isLoading, isConnected }: OverviewStatsProps) {
  if (isLoading || !isConnected) {
    return <Skeleton className="h-[200px] w-full" />;
  }

  if (!data) return null;

  const open = data.open_24h;
  const prevClose = open;
  const volume24h = data.volume_24h ?? data.volume;

  const stats: Array<{
    label: string;
    value: number;
    prefix?: string;
    suffix?: string;
    compact?: boolean;
  }> = [];

  const addStat = (
    label: string,
    value: number | undefined,
    options?: { prefix?: string; suffix?: string; compact?: boolean }
  ) => {
    if (value === undefined || value === null || Number.isNaN(value)) return;
    stats.push({ label, value, ...options });
  };

  addStat('Prev Close', prevClose, { prefix: '$' });
  addStat('24H Volume', volume24h, { prefix: '$', compact: true });
  addStat('24H High', data.high_24h, { prefix: '$' });
  addStat('Open', open, { prefix: '$' });
  addStat('24H Low', data.low_24h, { prefix: '$' });

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 gap-px bg-slate-800 border border-slate-800 rounded-lg overflow-hidden">
      {stats.map((stat, i) => (
        <div key={i} className="bg-slate-950/50 p-4 flex justify-between items-center group hover:bg-slate-900/80 transition-colors">
          <span className="text-sm text-slate-400 group-hover:text-slate-300">{stat.label}</span>
          <span className="font-mono font-medium text-slate-200">
             {stat.prefix}
             {formatNumber(stat.value, stat.compact ? 0 : 2)}
             {stat.suffix}
          </span>
        </div>
      ))}
    </div>
  );
}

