import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { TickerData } from '@/hooks/api/usePriceData';

interface PriceStatsProps {
  data?: TickerData;
  isLoading: boolean;
}

export function PriceStats({ data, isLoading }: PriceStatsProps) {
  if (isLoading) {
    return <Skeleton className="h-[400px] w-full" />;
  }

  if (!data) return null;

  const open = data.open_24h ?? data.price - (data.price_change_24h || 0);

  const items = [
    { label: 'Close', value: data.price },
    { label: 'Open', value: open },
    { label: 'High', value: data.high_24h },
    { label: 'Low', value: data.low_24h },
  ];

  const volume = data.volume_24h || data.volume; // Use 24h volume if available

  return (
    <Card>
      <CardContent className="p-4 space-y-4">
        <div className="grid grid-cols-2 gap-4">
          {items.map((item) => (
            <div key={item.label} className="flex flex-col">
              <span className="text-muted-foreground text-sm">{item.label}</span>
              <span className="font-mono font-medium">
                ${item.value?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) || '-'}
              </span>
            </div>
          ))}
        </div>
        
        <div className="pt-4 border-t border-border">
          <div className="flex justify-between items-center mb-1">
            <span className="text-muted-foreground text-sm">Volume</span>
            <span className="font-mono font-medium">{volume?.toLocaleString() || '-'}</span>
          </div>
          {/* Volume bar placeholder if needed */}
        </div>
      </CardContent>
    </Card>
  );
}

