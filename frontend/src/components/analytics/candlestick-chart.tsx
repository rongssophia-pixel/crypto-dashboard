'use client';

/**
 * Candlestick Chart Component
 * OHLCV visualization using Recharts
 */

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import {
  ResponsiveContainer,
  ComposedChart,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
} from 'recharts';
import { formatDateTime } from '@/lib/time';

interface CandleData {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface CandlestickChartProps {
  data?: CandleData[];
  isLoading?: boolean;
  error?: string;
  interval: string;
  onIntervalChange: (interval: string) => void;
}

const INTERVALS = [
  { label: '1 Minute', value: '1m' },
  { label: '5 Minutes', value: '5m' },
  { label: '15 Minutes', value: '15m' },
  { label: '1 Hour', value: '1h' },
  { label: '4 Hours', value: '4h' },
  { label: '1 Day', value: '1d' },
];

const Candlestick = (props: any) => {
  const {
    x,
    y,
    width,
    height,
    payload,
  } = props;

  const { open, close, high, low } = payload;
  const isGrowing = close > open;
  // Use tailwind colors: green-500 (#22c55e) and red-500 (#ef4444)
  const color = isGrowing ? '#22c55e' : '#ef4444';

  if (low === high) return null;

  // Calculate coordinates based on the bar's dimensions
  // The bar is rendered from 'y' (top value, which is high) with 'height' (high - low)
  const ratio = height / (high - low);
  
  // Coordinate system: y increases downwards
  // y corresponds to high
  // y + height corresponds to low
  
  const yOpen = y + (high - open) * ratio;
  const yClose = y + (high - close) * ratio;
  
  const bodyTop = Math.min(yOpen, yClose);
  const bodyHeight = Math.abs(yOpen - yClose);
  
  return (
    <g stroke={color} fill={color} strokeWidth="1.5">
      {/* Wick */}
      <line
        x1={x + width / 2}
        y1={y}
        x2={x + width / 2}
        y2={y + height}
      />
      {/* Body */}
      <rect
        x={x}
        y={bodyTop}
        width={width}
        height={Math.max(1, bodyHeight)} // Ensure at least 1px visible
        fill={color}
      />
    </g>
  );
};

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    // payload[0] is the first active data item (Candle or Volume)
    const data = payload[0].payload;
    
    // Format numbers
    const fmt = (val: number) => val.toLocaleString(undefined, { maximumFractionDigits: 2 });
    
    return (
      <div className="bg-background border border-border p-3 rounded-lg shadow-lg text-xs z-50">
        <p className="font-bold mb-2 text-sm">{label}</p>
        <div className="space-y-1">
          <div className="flex justify-between gap-4">
            <span className="text-muted-foreground">Open:</span>
            <span className="font-mono">{fmt(data.open)}</span>
          </div>
          <div className="flex justify-between gap-4">
            <span className="text-muted-foreground">High:</span>
            <span className="font-mono">{fmt(data.high)}</span>
          </div>
          <div className="flex justify-between gap-4">
            <span className="text-muted-foreground">Low:</span>
            <span className="font-mono">{fmt(data.low)}</span>
          </div>
          <div className="flex justify-between gap-4">
            <span className="text-muted-foreground">Close:</span>
            <span className={`font-mono ${data.close > data.open ? 'text-green-500' : 'text-red-500'}`}>
              {fmt(data.close)}
            </span>
          </div>
          <div className="flex justify-between gap-4 mt-2 pt-2 border-t border-border">
            <span className="text-muted-foreground">Volume:</span>
            <span className="font-mono">{fmt(data.volume)}</span>
          </div>
        </div>
      </div>
    );
  }
  return null;
};

export function CandlestickChart({
  data = [],
  isLoading = false,
  error,
  interval,
  onIntervalChange,
}: CandlestickChartProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Price Chart</CardTitle>
          <CardDescription>OHLCV candlestick data</CardDescription>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-[550px] w-full" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Price Chart</CardTitle>
          <CardDescription>OHLCV candlestick data</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-[550px]">
            <p className="text-sm text-muted-foreground">{error}</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!data.length) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Price Chart</CardTitle>
          <CardDescription>OHLCV candlestick data</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-[550px]">
            <p className="text-sm text-muted-foreground">
              No data available for the selected time range
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Reverse data to show oldest to newest (left to right)
  const reversedData = [...data].reverse();

  // Transform data for chart
  const dateFormat = interval === '1d' || interval === '1w' ? 'MMM dd' : 'HH:mm';
  const chartData = reversedData.map((item) => ({
    time: formatDateTime(item.timestamp, dateFormat),
    // Pass range [low, high] so Recharts scales the bar correctly
    range: [item.low, item.high],
    open: item.open,
    close: item.close,
    high: item.high,
    low: item.low,
    volume: item.volume,
    timestamp: item.timestamp,
    // Helper for color
    isUp: item.close > item.open,
  }));
  
  // Calculate min/max for domain to prevent chart from starting at 0 if prices are high
  const allLows = data.map(d => d.low);
  const allHighs = data.map(d => d.high);
  const minPrice = Math.min(...allLows);
  const maxPrice = Math.max(...allHighs);
  const buffer = (maxPrice - minPrice) * 0.1;

  // Calculate volume min/max to improve visual scaling
  const allVolumes = data.map(d => d.volume);
  const minVolume = Math.min(...allVolumes);
  const maxVolume = Math.max(...allVolumes);
  // Start from 0 to show absolute scale, but if variations are small relative to total, 
  // users might prefer auto or dataMin. 
  // However, "all bars same height" usually means max is too big or min is too high.
  // If bars look same height (and not small), it means they are all close to max?
  // Or maybe user wants logarithmic scale?
  // Let's try domain={['auto', 'auto']} which means usually 0 to max. 
  // If they look same height, maybe data is uniform.
  // But if the user complains, maybe we should try to exaggerate differences:
  // domain={[minVolume * 0.9, maxVolume * 1.05]}
  // Let's try setting domain to 'dataMin' 'dataMax' for volume to show fluctuations better.

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Price Chart</CardTitle>
            <CardDescription>OHLCV candlestick data</CardDescription>
          </div>
          <div className="space-y-2 w-40">
            <Label className="text-xs">Interval</Label>
            <Select value={interval} onValueChange={onIntervalChange}>
              <SelectTrigger className="h-8 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {INTERVALS.map((int) => (
                  <SelectItem key={int.value} value={int.value}>
                    {int.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="h-[550px] flex flex-col">
          {/* Price Chart */}
          <div className="flex-1 min-h-0">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={chartData} syncId="candlestick">
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted/30" vertical={false} />
                <XAxis
                  dataKey="time"
                  hide // Hide X axis for the top chart
                />
                <YAxis
                  yAxisId="price"
                  orientation="left" // Move to left
                  tick={{ fontSize: 12 }}
                  className="text-muted-foreground"
                  domain={[minPrice - buffer, maxPrice + buffer]}
                  tickFormatter={(value) => value.toLocaleString()}
                />
                <Tooltip content={<CustomTooltip />} />
                <Bar
                  yAxisId="price"
                  dataKey="range"
                  shape={<Candlestick />}
                  barSize={10}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>

          {/* Volume Chart */}
          <div className="h-[150px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} syncId="candlestick">
                <XAxis
                  dataKey="time"
                  tick={{ fontSize: 12 }}
                  className="text-muted-foreground"
                  minTickGap={30}
                />
                <YAxis
                  orientation="left"
                  tick={{ fontSize: 12 }}
                  className="text-muted-foreground"
                  domain={['dataMin', 'dataMax']}
                  tickFormatter={(value) => (value >= 1000000 ? `${(value / 1000000).toFixed(1)}M` : value >= 1000 ? `${(value / 1000).toFixed(1)}K` : value)}
                />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="volume" barSize={10}>
                  {chartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.isUp ? '#22c55e' : '#ef4444'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
