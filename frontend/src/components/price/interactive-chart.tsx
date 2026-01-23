'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import {
  ResponsiveContainer,
  ComposedChart,
  BarChart,
  Line,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
  Area,
} from 'recharts';
import { formatDateTime, TimeRangePreset } from '@/lib/time';
import { CandleData, usePriceCandles } from '@/hooks/api/usePriceData';
import { Maximize2, Settings, Share2, PlusCircle } from 'lucide-react';

interface InteractiveChartProps {
  symbol: string;
  range?: TimeRangePreset;
  onRangeChange?: (range: TimeRangePreset) => void;
}

const RANGES: TimeRangePreset[] = ['1D', '5D', '1M', '6M', 'YTD', '1Y', '5Y', 'MAX'];

export function InteractiveChart({ symbol, range: controlledRange, onRangeChange }: InteractiveChartProps) {
  const [internalRange, setInternalRange] = useState<TimeRangePreset>('1D');
  const [chartType, setChartType] = useState<'candle' | 'line'>('line');
  
  const range = controlledRange || internalRange;
  const setRange = (r: TimeRangePreset) => {
    if (onRangeChange) {
      onRangeChange(r);
    } else {
      setInternalRange(r);
    }
  };
  
  const { data, isLoading, error } = usePriceCandles(symbol, range);
  const candles = data?.candles || [];

  // Transform data
  const chartData = [...candles].reverse().map(item => ({
    time: item.timestamp, // Keep raw ISO for tooltip formatting
    displayTime: formatDateTime(item.timestamp, range === '1D' ? 'HH:mm' : 'MMM dd'),
    open: item.open,
    high: item.high,
    low: item.low,
    close: item.close,
    volume: item.volume,
    isUp: item.close >= item.open,
    // For candlestick range
    range: [item.low, item.high],
  }));

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const d = payload[0].payload;
      return (
        <div className="bg-background/95 border border-border p-3 rounded-lg shadow-xl text-xs backdrop-blur-sm z-50 min-w-[180px]">
          <p className="font-medium mb-2 text-muted-foreground">{formatDateTime(d.time)}</p>
          <div className="space-y-1">
            <div className="flex justify-between">
               <span>Close</span>
               <span className={`font-mono font-medium ${d.isUp ? 'text-green-500' : 'text-red-500'}`}>
                 ${d.close.toLocaleString()}
               </span>
            </div>
            <div className="flex justify-between">
               <span>Open</span>
               <span className="font-mono">${d.open.toLocaleString()}</span>
            </div>
            <div className="flex justify-between">
               <span>High</span>
               <span className="font-mono">${d.high.toLocaleString()}</span>
            </div>
            <div className="flex justify-between">
               <span>Low</span>
               <span className="font-mono">${d.low.toLocaleString()}</span>
            </div>
            <div className="flex justify-between mt-2 pt-2 border-t border-border/50">
               <span>Volume</span>
               <span className="font-mono">{d.volume.toLocaleString()}</span>
            </div>
          </div>
        </div>
      );
    }
    return null;
  };

  // Min/Max for Y-axis scaling
  const minPrice = chartData.length > 0 ? Math.min(...chartData.map(d => d.low)) : 0;
  const maxPrice = chartData.length > 0 ? Math.max(...chartData.map(d => d.high)) : 0;
  const buffer = (maxPrice - minPrice) * 0.05;

  const EmptyTooltip = () => null;

  return (
    <Card className="border-none shadow-none bg-transparent">
      <CardHeader className="px-0 pt-0 pb-4">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div className="flex items-center gap-2 overflow-x-auto w-full sm:w-auto pb-2 sm:pb-0 no-scrollbar">
            {RANGES.map((r) => (
              <Button
                key={r}
                variant={range === r ? "secondary" : "ghost"}
                size="sm"
                onClick={() => setRange(r)}
                className="rounded-full px-3 h-7 text-xs font-medium"
              >
                {r}
              </Button>
            ))}
          </div>
          
          <div className="flex items-center gap-2">
            <Button variant="outline" size="icon" className="h-8 w-8" onClick={() => setChartType(chartType === 'line' ? 'candle' : 'line')}>
                {/* Toggle icon based on type */}
               <span className="text-xs font-bold">{chartType === 'line' ? 'Line' : 'Candle'}</span>
            </Button>
            <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground">
              <Share2 className="w-4 h-4" />
            </Button>
            <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground">
              <Maximize2 className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="px-0">
        {isLoading ? (
           <Skeleton className="h-[400px] w-full" />
        ) : error ? (
           <div className="h-[400px] flex items-center justify-center text-muted-foreground">
             Failed to load chart data
           </div>
        ) : chartData.length === 0 ? (
           <div className="h-[400px] flex items-center justify-center text-muted-foreground">
             No data available
           </div>
        ) : (
          <div className="h-[450px] flex flex-col">
            <div className="flex-1 min-h-0">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={chartData}>
                  <defs>
                    <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#22c55e" stopOpacity={0.2}/>
                      <stop offset="95%" stopColor="#22c55e" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--muted))" opacity={0.2} />
                  <XAxis 
                    dataKey="displayTime" 
                    hide 
                  />
                  <YAxis 
                    orientation="right" 
                    domain={[minPrice - buffer, maxPrice + buffer]}
                    tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
                    axisLine={false}
                    tickLine={false}
                    width={50}
                    tickFormatter={(val) => val.toFixed(2)}
                  />
                  <Tooltip content={<CustomTooltip />} cursor={{ stroke: 'hsl(var(--muted-foreground))', strokeWidth: 1, strokeDasharray: '4 4' }} />
                  
                  {chartType === 'line' ? (
                    <Area 
                      type="monotone" 
                      dataKey="close" 
                      stroke="#22c55e" 
                      fillOpacity={1} 
                      fill="url(#colorPrice)" 
                      strokeWidth={2}
                    />
                  ) : (
                     <Bar
                        dataKey="range"
                        // Custom shape logic would be needed for true candlestick
                        // Reusing simple bar for now or just stick to Line for the main view as requested "like the picture"
                        // The picture shows a line/area chart.
                        fill="#22c55e" // Simplified
                     >
                       {chartData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.isUp ? '#22c55e' : '#ef4444'} />
                       ))}
                     </Bar>
                  )}
                  
                </ComposedChart>
              </ResponsiveContainer>
            </div>
            
            <div className="h-[60px] mt-2">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData}>
                   <XAxis 
                      dataKey="displayTime" 
                      tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }}
                      axisLine={false}
                      tickLine={false}
                      minTickGap={50}
                   />
                   <Tooltip cursor={false} content={<EmptyTooltip />} />
                   <Bar dataKey="volume" fill="hsl(var(--muted))" opacity={0.3} barSize={2} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
