'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
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
  Area,
} from 'recharts';
import { formatDateTime, TimeRangePreset } from '@/lib/time';
import { formatNumber } from '@/lib/utils';
import { usePriceCandles } from '@/hooks/api/usePriceData';
import { Maximize2, Share2 } from 'lucide-react';

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

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const d = payload[0].payload;
      return (
        <div className="bg-background/95 border border-border p-3 rounded-lg shadow-xl text-xs backdrop-blur-sm z-50 min-w-[180px]">
          <p className="font-medium mb-2 text-muted-foreground">{formatDateTime(d.time)}</p>
          <div className="space-y-1">
            <div className="flex justify-between">
               <span>Close</span>
               <span className={`font-mono font-medium ${d.isUp ? 'text-green-500' : 'text-red-500'}`}>
                 ${formatNumber(d.close)}
               </span>
            </div>
            <div className="flex justify-between">
               <span>Open</span>
               <span className="font-mono">${formatNumber(d.open)}</span>
            </div>
            <div className="flex justify-between">
               <span>High</span>
               <span className="font-mono">${formatNumber(d.high)}</span>
            </div>
            <div className="flex justify-between">
               <span>Low</span>
               <span className="font-mono">${formatNumber(d.low)}</span>
            </div>
            <div className="flex justify-between mt-2 pt-2 border-t border-border/50">
               <span>Volume</span>
               <span className="font-mono">{formatNumber(d.volume)}</span>
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
    <Card className="border-none shadow-none bg-transparent h-full flex flex-col">
      <CardHeader className="px-0 pt-0 pb-2 shrink-0 border-b border-slate-800/60 mb-2">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div className="flex items-center gap-1 overflow-x-auto w-full sm:w-auto pb-2 sm:pb-0 no-scrollbar">
            {RANGES.map((r) => (
              <Button
                key={r}
                variant={range === r ? "secondary" : "ghost"}
                size="sm"
                onClick={() => setRange(r)}
                className={`rounded-md px-3 h-8 text-xs font-medium transition-all ${
                  range === r 
                    ? "bg-slate-800 text-slate-100 shadow-sm" 
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
                }`}
              >
                {r}
              </Button>
            ))}
            <div className="w-px h-4 bg-slate-800 mx-2" />
            <Button variant="ghost" size="icon" className="h-8 w-8 text-slate-400 hover:text-slate-200" onClick={() => {}}>
               <span className="sr-only">Calendar</span>
               <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4"><rect width="18" height="18" x="3" y="4" rx="2" ry="2"/><line x1="16" x2="16" y1="2" y2="6"/><line x1="8" x2="8" y1="2" y2="6"/><line x1="3" x2="21" y1="10" y2="10"/></svg>
            </Button>
          </div>
          
          <div className="flex items-center gap-1">
            <Button 
                variant="ghost" 
                size="sm" 
                className={`h-8 px-2 text-xs font-medium gap-2 ${chartType === 'line' ? 'bg-slate-800/50 text-slate-200' : 'text-slate-400'}`}
                onClick={() => setChartType('line')}
            >
               <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
               <span className="hidden sm:inline">Line</span>
            </Button>
            <Button 
                variant="ghost" 
                size="sm" 
                className={`h-8 px-2 text-xs font-medium gap-2 ${chartType === 'candle' ? 'bg-slate-800/50 text-slate-200' : 'text-slate-400'}`}
                onClick={() => setChartType('candle')}
            >
               <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4"><path d="M17 3v18"/><path d="M7 3v18"/><rect width="8" height="8" x="3" y="8" rx="1"/><rect width="8" height="8" x="13" y="8" rx="1"/></svg>
               <span className="hidden sm:inline">Candle</span>
            </Button>
            
            <div className="w-px h-4 bg-slate-800 mx-2" />
            
            <Button variant="ghost" size="icon" className="h-8 w-8 text-slate-400 hover:text-slate-200">
              <Share2 className="w-4 h-4" />
            </Button>
            <Button variant="ghost" size="icon" className="h-8 w-8 text-slate-400 hover:text-slate-200">
              <Maximize2 className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="px-0 flex-1 min-h-0">
        {isLoading ? (
           <Skeleton className="h-full w-full" />
        ) : error ? (
           <div className="h-full flex items-center justify-center text-muted-foreground">
             Failed to load chart data
           </div>
        ) : chartData.length === 0 ? (
           <div className="h-full flex items-center justify-center text-muted-foreground">
             No data available
           </div>
        ) : (
          <div className="flex flex-col h-full">
            <div className="flex-1 min-h-0">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={chartData}>
                  <defs>
                    <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#22c55e" stopOpacity={0.2}/>
                      <stop offset="95%" stopColor="#22c55e" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#334155" opacity={0.2} />
                  <XAxis 
                    dataKey="displayTime" 
                    hide 
                  />
                  <YAxis 
                    orientation="right" 
                    domain={[minPrice - buffer, maxPrice + buffer]}
                    tick={{ fontSize: 11, fill: '#94a3b8' }}
                    axisLine={false}
                    tickLine={false}
                    width={50}
                    tickFormatter={(val) => formatNumber(val)}
                  />
                  <Tooltip content={<CustomTooltip />} cursor={{ stroke: '#94a3b8', strokeWidth: 1, strokeDasharray: '4 4' }} />
                  
                  {chartType === 'line' ? (
                    <Area 
                      type="monotone" 
                      dataKey="close" 
                      stroke="#22c55e" 
                      fill="url(#colorPrice)" 
                      fillOpacity={1}
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
                      tick={{ fontSize: 10, fill: '#94a3b8' }}
                      axisLine={false}
                      tickLine={false}
                      minTickGap={50}
                   />
                   <Tooltip cursor={false} content={<EmptyTooltip />} />
                   <Bar dataKey="volume" fill="#94a3b8" opacity={0.3} barSize={2} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
