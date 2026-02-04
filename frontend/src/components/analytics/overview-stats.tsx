import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { TickerData } from '@/hooks/api/usePriceData';
import { formatNumber } from '@/lib/utils';

interface OverviewStatsProps {
  data?: TickerData;
  isLoading: boolean;
}

export function OverviewStats({ data, isLoading }: OverviewStatsProps) {
  if (isLoading) {
    return <Skeleton className="h-[200px] w-full" />;
  }

  if (!data) return null;

  // Derived or mock values for demonstration where API doesn't provide them
  const prevClose = data.price - (data.price_change_24h || 0);
  const open = prevClose; // Simplified approximation
  const mktCap = data.price * 19000000; // Mock calculation for BTC
  
  const stats = [
    { label: 'Prev Close', value: prevClose, prefix: '$' },
    { label: '24H Volume', value: data.volume_24h || data.volume, prefix: '$', compact: true },
    { label: '24H High', value: data.high_24h, prefix: '$' },
    
    { label: 'Open', value: open, prefix: '$' },
    { label: '24H Low', value: data.low_24h, prefix: '$' },
    { label: 'Year High', value: data.high_24h * 1.5, prefix: '$' }, // Mock
    
    { label: 'Year Low', value: data.low_24h * 0.5, prefix: '$' }, // Mock
    { label: 'Funding Rate', value: 0.01, suffix: '%' }, // Mock
    { label: 'Market Cap', value: mktCap, prefix: '$', compact: true },
  ];

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

