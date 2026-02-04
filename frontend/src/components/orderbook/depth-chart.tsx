'use client';

/**
 * Depth Chart (Orderbook)
 * Renders cumulative bid/ask depth from top-N levels.
 */

import { useMemo } from 'react';
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

export function DepthChartPlot({
  book,
  height = 220,
  theme = 'dark',
}: {
  book: OrderbookSnapshot | null;
  height?: number | string;
  theme?: 'dark' | 'light';
}) {
  const data = useMemo(() => {
    const bids = book?.bids || [];
    const asks = book?.asks || [];
    const bidDepth = buildDepth(bids, 'bid');
    const askDepth = buildDepth(asks, 'ask');
    return mergeDepth(bidDepth, askDepth);
  }, [book]);

  const hasLevels = Boolean((book?.bids?.length || 0) + (book?.asks?.length || 0));

  const tickFill = theme === 'dark' ? '#94a3b8' : 'hsl(var(--muted-foreground))';
  const gridStroke = theme === 'dark' ? '#334155' : 'hsl(var(--muted))';

  if (!hasLevels) {
    return (
      <div style={{ height }} className="flex items-center justify-center text-sm text-slate-400">
        Waiting for orderbook updates…
      </div>
    );
  }

  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.35} stroke={gridStroke} />
          <XAxis
            dataKey="price"
            type="number"
            domain={['dataMin', 'dataMax']}
            tickFormatter={(v) => formatNumber(v)}
            tick={{ fontSize: 11, fill: tickFill }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tickFormatter={(v) => formatNumber(v)}
            tick={{ fontSize: 11, fill: tickFill }}
            axisLine={false}
            tickLine={false}
            width={56}
          />
          <Tooltip
            formatter={(value: any, name: any) => [formatNumber(value), name]}
            labelFormatter={(label: any) => `Price: ${formatNumber(label)}`}
          />

          <defs>
            <linearGradient id="bidFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#22c55e" stopOpacity={0.28} />
              <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="askFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#ef4444" stopOpacity={0.24} />
              <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
            </linearGradient>
          </defs>

          <Area
            type="stepAfter"
            dataKey="bidDepth"
            name="Bid"
            stroke="#22c55e"
            fill="url(#bidFill)"
            strokeWidth={2}
            connectNulls
          />
          <Area
            type="stepAfter"
            dataKey="askDepth"
            name="Ask"
            stroke="#ef4444"
            fill="url(#askFill)"
            strokeWidth={2}
            connectNulls
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

// Backward compatible wrapper (existing usage)
export function DepthChart({ symbol, book }: { symbol: string; book: OrderbookSnapshot | null }) {
  return (
    <div className="rounded-xl border bg-background">
      <div className="flex items-center justify-between px-4 py-3 border-b">
        <div className="font-semibold">Depth Chart</div>
        <div className="text-sm text-muted-foreground">{symbol}</div>
      </div>
      <div className="p-4">
        <DepthChartPlot book={book} height={420} theme="light" />
      </div>
    </div>
  );
}

