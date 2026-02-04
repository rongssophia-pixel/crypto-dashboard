'use client';

/**
 * Depth Chart (Orderbook)
 * Renders cumulative bid/ask depth from top-N levels.
 */

import { useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts';
import { formatNumber } from '@/lib/utils';
import type { OrderbookLevel, OrderbookSnapshot } from '@/hooks/useRealtimeOrderbook';

type DepthPoint = {
  price: number;
  bidDepth?: number | null;
  askDepth?: number | null;
};

function buildDepth(levels: OrderbookLevel[], side: 'bid' | 'ask'): DepthPoint[] {
  const sorted = [...levels].sort((a, b) =>
    side === 'bid' ? b[0] - a[0] : a[0] - b[0]
  );
  let cum = 0;
  const points: DepthPoint[] = sorted.map(([price, size]) => {
    cum += size;
    return side === 'bid' ? { price, bidDepth: cum } : { price, askDepth: cum };
  });

  // For bids we want ascending price left->right
  return side === 'bid' ? points.reverse() : points;
}

function mergeDepth(bids: DepthPoint[], asks: DepthPoint[]): DepthPoint[] {
  // Ensure both keys exist on every point (Recharts behaves better with nulls than undefined)
  const all = [...bids, ...asks]
    .sort((a, b) => a.price - b.price)
    .map((p) => ({
      price: p.price,
      bidDepth: p.bidDepth ?? null,
      askDepth: p.askDepth ?? null,
    }));
  return all;
}

export function DepthChart({
  symbol,
  book,
}: {
  symbol: string;
  book: OrderbookSnapshot | null;
}) {
  const data = useMemo(() => {
    const bids = book?.bids || [];
    const asks = book?.asks || [];
    const bidDepth = buildDepth(bids, 'bid');
    const askDepth = buildDepth(asks, 'ask');
    return mergeDepth(bidDepth, askDepth);
  }, [book]);

  const bestBid = book?.bids?.length ? book.bids[0][0] : null;
  const bestAsk = book?.asks?.length ? book.asks[0][0] : null;
  const hasLevels = Boolean((book?.bids?.length || 0) + (book?.asks?.length || 0));

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center justify-between">
          <span>Depth Chart</span>
          <span className="text-sm font-normal text-muted-foreground">{symbol}</span>
        </CardTitle>
        <div className="text-xs text-muted-foreground flex flex-wrap gap-x-4 gap-y-1">
          <span>
            Best Bid:{' '}
            <span className="font-mono text-foreground">
              {bestBid ? formatNumber(bestBid) : '—'}
            </span>
          </span>
          <span>
            Best Ask:{' '}
            <span className="font-mono text-foreground">
              {bestAsk ? formatNumber(bestAsk) : '—'}
            </span>
          </span>
          {book?.spread != null && (
            <span>
              Spread:{' '}
              <span className="font-mono text-foreground">{formatNumber(book.spread)}</span>
            </span>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {!hasLevels ? (
          <div className="h-[420px] flex items-center justify-center text-sm text-muted-foreground">
            Waiting for orderbook updates…
          </div>
        ) : (
          <div className="h-[420px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.2} />
              <XAxis
                dataKey="price"
                type="number"
                domain={['dataMin', 'dataMax']}
                tickFormatter={(v) => formatNumber(v)}
                tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tickFormatter={(v) => formatNumber(v)}
                tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
                axisLine={false}
                tickLine={false}
                width={60}
              />
              <Tooltip
                formatter={(value: any, name: any) => [formatNumber(value), name]}
                labelFormatter={(label: any) => `Price: ${formatNumber(label)}`}
              />

              <defs>
                <linearGradient id="bidFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#22c55e" stopOpacity={0.25} />
                  <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="askFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ef4444" stopOpacity={0.22} />
                  <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                </linearGradient>
              </defs>

              <Area
                type="stepAfter"
                dataKey="bidDepth"
                name="Bid Depth"
                stroke="#22c55e"
                fill="url(#bidFill)"
                strokeWidth={2}
                connectNulls
              />
              <Area
                type="stepAfter"
                dataKey="askDepth"
                name="Ask Depth"
                stroke="#ef4444"
                fill="url(#askFill)"
                strokeWidth={2}
                connectNulls
              />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>
  );
}


