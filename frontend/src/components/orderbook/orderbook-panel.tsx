'use client';

/**
 * Orderbook Panel (pro-style)
 * Bid/ask imbalance bar + best bid/ask + embedded depth plot + 20×2 ladder.
 */

import { useMemo } from 'react';
import { cn, formatNumber } from '@/lib/utils';
import type { OrderbookSnapshot, OrderbookLevel } from '@/hooks/useRealtimeOrderbook';
import { Badge } from '@/components/ui/badge';
import { DepthChartPlot } from '@/components/orderbook/depth-chart';

function sumNotional(levels: OrderbookLevel[]) {
  return levels.reduce((acc, [p, q]) => acc + p * q, 0);
}

function topBids(bids: OrderbookLevel[], n: number) {
  return [...bids].sort((a, b) => b[0] - a[0]).slice(0, n);
}

function topAsks(asks: OrderbookLevel[], n: number) {
  return [...asks].sort((a, b) => a[0] - b[0]).slice(0, n);
}

function maxSize(levels: OrderbookLevel[]) {
  return Math.max(1, ...levels.map((l) => (Number.isFinite(l[1]) ? l[1] : 0)));
}

function LadderRow({
  side,
  price,
  size,
  fillPct,
  className,
}: {
  side: 'bid' | 'ask';
  price: number;
  size: number;
  fillPct: number;
  className?: string;
}) {
  const isBid = side === 'bid';
  return (
    <div
      className={cn(
        'relative h-10 flex items-center px-3 overflow-hidden',
        'border-b border-slate-800/70 last:border-b-0',
        className
      )}
    >
      {/* Heat fill */}
      <div
        className={cn(
          'absolute inset-y-0',
          isBid ? 'left-0 bg-emerald-500/18' : 'right-0 bg-red-500/18'
        )}
        style={{ width: `${Math.min(100, Math.max(0, fillPct))}%` }}
      />

      {/* Content */}
      <div className="relative z-10 w-full flex items-center justify-between gap-2">
        <div className={cn('font-mono tabular-nums', isBid ? 'text-emerald-400' : 'text-red-400')}>
          {formatNumber(price)}
        </div>
        <div className="font-mono tabular-nums text-slate-200">{formatNumber(size)}</div>
      </div>
    </div>
  );
}

export function OrderbookPanel({
  symbol,
  book,
  levels = 20,
  showChart = true,
}: {
  symbol: string;
  book: OrderbookSnapshot | null;
  levels?: number;
  showChart?: boolean;
}) {
  const { bids, asks, bestBid, bestAsk, bidPct, askPct, bidRows, askRows } = useMemo(() => {
    const bids = topBids(book?.bids || [], levels);
    const asks = topAsks(book?.asks || [], levels);
    const bestBid = bids[0]?.[0] ?? null;
    const bestAsk = asks[0]?.[0] ?? null;

    const bidNotional = sumNotional(bids);
    const askNotional = sumNotional(asks);
    const total = bidNotional + askNotional;
    const bidPct = total > 0 ? (bidNotional / total) * 100 : 50;
    const askPct = 100 - bidPct;

    const bidMax = maxSize(bids);
    const askMax = maxSize(asks);

    const bidRows = bids.map(([p, q]) => ({ p, q, pct: (q / bidMax) * 100 }));
    const askRows = asks.map(([p, q]) => ({ p, q, pct: (q / askMax) * 100 }));

    return { bids, asks, bestBid, bestAsk, bidPct, askPct, bidRows, askRows };
  }, [book, levels]);

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950 text-slate-100 overflow-hidden">
      {/* Top header */}
      <div className="px-5 pt-4 pb-3">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-baseline gap-3">
            <div className="text-lg font-semibold tracking-tight">Order Book</div>
            <Badge className="bg-slate-800 text-slate-200 border-slate-700" variant="outline">
              {symbol}
            </Badge>
            <Badge className="bg-slate-900 text-slate-300 border-slate-800" variant="outline">
              {levels}
            </Badge>
          </div>
          <div className="text-xs text-slate-400">
            {book?.exchange ? String(book.exchange).toUpperCase() : 'BINANCE'}
          </div>
        </div>

        {/* Bid/Ask imbalance bar */}
        <div className="mt-3">
          <div className="flex items-center justify-between text-sm">
            <div className="text-emerald-400">Bid</div>
            <div className="text-slate-300">Ask</div>
          </div>
          <div className="mt-2 h-2 w-full rounded-full bg-slate-800 overflow-hidden">
            <div className="h-full bg-emerald-500" style={{ width: `${bidPct}%` }} />
          </div>
          <div className="mt-2 flex items-center justify-between text-sm">
            <div className="text-emerald-400 tabular-nums">{bidPct.toFixed(2)}%</div>
            <div className="text-red-400 tabular-nums">{askPct.toFixed(2)}%</div>
          </div>
        </div>

        {/* Best bid/ask */}
        <div className="mt-4 grid grid-cols-2 gap-6">
          <div className="rounded-xl bg-slate-900/60 border border-slate-800 p-4">
            <div className="text-xs text-slate-400">Best Bid</div>
            <div className="mt-1 font-mono text-2xl tabular-nums text-emerald-400">
              {bestBid != null ? formatNumber(bestBid) : '—'}
            </div>
            <div className="mt-1 text-xs text-slate-500">
              levels: {bids.length}
            </div>
          </div>
          <div className="rounded-xl bg-slate-900/60 border border-slate-800 p-4">
            <div className="text-xs text-slate-400">Best Ask</div>
            <div className="mt-1 font-mono text-2xl tabular-nums text-red-400">
              {bestAsk != null ? formatNumber(bestAsk) : '—'}
            </div>
            <div className="mt-1 text-xs text-slate-500">
              levels: {asks.length}
            </div>
          </div>
        </div>
      </div>

      {/* Depth chart */}
      {showChart && (
        <div className="px-5 pb-4">
          <DepthChartPlot book={book} height={220} theme="dark" />
        </div>
      )}

      {/* Ladder */}
      <div className="grid grid-cols-2 border-t border-slate-800">
        <div className="border-r border-slate-800">
          <div className="px-3 py-2 text-xs text-slate-400 bg-slate-950/60 border-b border-slate-800">
            Price / Size
          </div>
          {bidRows.length ? (
            bidRows.map((r, idx) => (
              <LadderRow key={`b-${idx}-${r.p}`} side="bid" price={r.p} size={r.q} fillPct={r.pct} />
            ))
          ) : (
            <div className="p-4 text-sm text-slate-400">No bids</div>
          )}
        </div>
        <div>
          <div className="px-3 py-2 text-xs text-slate-400 bg-slate-950/60 border-b border-slate-800 text-right">
            Price / Size
          </div>
          {askRows.length ? (
            askRows.map((r, idx) => (
              <LadderRow
                key={`a-${idx}-${r.p}`}
                side="ask"
                price={r.p}
                size={r.q}
                fillPct={r.pct}
                className="text-right"
              />
            ))
          ) : (
            <div className="p-4 text-sm text-slate-400 text-right">No asks</div>
          )}
        </div>
      </div>
    </div>
  );
}


