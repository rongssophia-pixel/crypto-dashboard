'use client';

/**
 * Archive Chart Component
 * Visualizes archive data with interactive charts
 */

import { useState, useMemo } from 'react';
import { useArchiveData } from '@/hooks/api/useArchiveData';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Loader2, Search } from 'lucide-react';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { format } from 'date-fns';

interface ArchiveChartProps {
  archiveId: string;
}

export default function ArchiveChart({ archiveId }: ArchiveChartProps) {
  const [symbolFilter, setSymbolFilter] = useState('');
  const [appliedFilter, setAppliedFilter] = useState('');

  const { data, isLoading, error } = useArchiveData({
    archiveId,
    limit: 1000, // Load more data for charting
    offset: 0,
    symbols: appliedFilter ? [appliedFilter] : undefined,
  });

  const handleApplyFilter = () => {
    setAppliedFilter(symbolFilter);
  };

  const handleClearFilter = () => {
    setSymbolFilter('');
    setAppliedFilter('');
  };

  // Prepare chart data
  const chartData = useMemo(() => {
    if (!data || !data.rows || data.rows.length === 0) return [];

    return data.rows
      .map((row) => {
        // Try to parse timestamp
        const timestamp = row.timestamp || row.time || row.created_at;
        let formattedTime = 'N/A';
        
        if (timestamp) {
          try {
            const date = new Date(timestamp);
            formattedTime = format(date, 'MMM d, HH:mm');
          } catch (e) {
            formattedTime = String(timestamp);
          }
        }

        return {
          time: formattedTime,
          timestamp: timestamp,
          price: parseFloat(String(row.price || 0)),
          volume: parseFloat(String(row.volume || row.quantity || 0)),
          // For candle data
          open: parseFloat(String(row.open || 0)),
          high: parseFloat(String(row.high || 0)),
          low: parseFloat(String(row.low || 0)),
          close: parseFloat(String(row.close || 0)),
        };
      })
      .filter((item) => item.price > 0 || item.close > 0) // Filter out invalid data
      .slice(0, 500); // Limit to 500 points for performance
  }, [data]);

  const hasCandles = useMemo(() => {
    return chartData.some((d) => d.open > 0 || d.high > 0 || d.low > 0 || d.close > 0);
  }, [chartData]);

  const hasPriceData = useMemo(() => {
    return chartData.some((d) => d.price > 0);
  }, [chartData]);

  const hasVolumeData = useMemo(() => {
    return chartData.some((d) => d.volume > 0);
  }, [chartData]);

  return (
    <div className="space-y-6">
      {/* Filter Controls */}
      <Card>
        <CardHeader>
          <CardTitle>Visualization Settings</CardTitle>
          <CardDescription>Filter data to visualize</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4 items-end">
            <div className="flex-1 max-w-xs">
              <Label htmlFor="chart-symbol-filter">Symbol</Label>
              <div className="flex gap-2">
                <Input
                  id="chart-symbol-filter"
                  placeholder="e.g., BTCUSDT"
                  value={symbolFilter}
                  onChange={(e) => setSymbolFilter(e.target.value.toUpperCase())}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      handleApplyFilter();
                    }
                  }}
                />
                <Button onClick={handleApplyFilter} size="icon">
                  <Search className="w-4 h-4" />
                </Button>
              </div>
            </div>
            {appliedFilter && (
              <Button variant="outline" onClick={handleClearFilter}>
                Clear Filter
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Charts */}
      {isLoading ? (
        <Card>
          <CardContent className="flex justify-center p-12">
            <Loader2 className="w-8 h-8 animate-spin text-primary" />
          </CardContent>
        </Card>
      ) : error ? (
        <Card>
          <CardContent className="p-12 text-center text-destructive">
            <p>Error loading chart data</p>
            <p className="text-sm text-muted-foreground mt-2">
              {error instanceof Error ? error.message : 'Unknown error'}
            </p>
          </CardContent>
        </Card>
      ) : chartData.length === 0 ? (
        <Card>
          <CardContent className="p-12 text-center text-muted-foreground">
            <p>No data to visualize</p>
            <p className="text-sm mt-2">Try selecting a specific symbol to view charts</p>
          </CardContent>
        </Card>
      ) : (
        <>
          {/* Price Chart */}
          {(hasPriceData || hasCandles) && (
            <Card>
              <CardHeader>
                <CardTitle>Price History</CardTitle>
                <CardDescription>
                  {hasCandles ? 'OHLC Candle Data' : 'Tick Price Data'}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={400}>
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="time"
                      tick={{ fontSize: 12 }}
                      angle={-45}
                      textAnchor="end"
                      height={80}
                    />
                    <YAxis
                      domain={['auto', 'auto']}
                      tick={{ fontSize: 12 }}
                      tickFormatter={(value) =>
                        value.toLocaleString(undefined, {
                          maximumFractionDigits: 2,
                        })
                      }
                    />
                    <Tooltip
                      formatter={(value: any) =>
                        parseFloat(value).toLocaleString(undefined, {
                          maximumFractionDigits: 8,
                        })
                      }
                    />
                    <Legend />
                    {hasPriceData && <Line type="monotone" dataKey="price" stroke="#8884d8" dot={false} />}
                    {hasCandles && (
                      <>
                        <Line type="monotone" dataKey="open" stroke="#82ca9d" dot={false} />
                        <Line type="monotone" dataKey="high" stroke="#ffc658" dot={false} />
                        <Line type="monotone" dataKey="low" stroke="#ff8042" dot={false} />
                        <Line type="monotone" dataKey="close" stroke="#8884d8" dot={false} />
                      </>
                    )}
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          )}

          {/* Volume Chart */}
          {hasVolumeData && (
            <Card>
              <CardHeader>
                <CardTitle>Volume History</CardTitle>
                <CardDescription>Trading volume over time</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="time"
                      tick={{ fontSize: 12 }}
                      angle={-45}
                      textAnchor="end"
                      height={80}
                    />
                    <YAxis
                      tick={{ fontSize: 12 }}
                      tickFormatter={(value) =>
                        value.toLocaleString(undefined, {
                          maximumFractionDigits: 2,
                        })
                      }
                    />
                    <Tooltip
                      formatter={(value: any) =>
                        parseFloat(value).toLocaleString(undefined, {
                          maximumFractionDigits: 8,
                        })
                      }
                    />
                    <Legend />
                    <Bar dataKey="volume" fill="#82ca9d" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}

