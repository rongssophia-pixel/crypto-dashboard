'use client';

/**
 * Metrics Display Component
 * Aggregated statistics cards
 */

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { TrendingUp, TrendingDown, Activity, DollarSign } from 'lucide-react';
import { formatPrice, formatNumber } from '@/lib/utils';

interface MetricsData {
  averagePrice: number;
  priceVolatility: number;
  totalVolume: number;
  high: number;
  low: number;
  tradeCount?: number;
}

interface MetricsDisplayProps {
  data?: MetricsData;
  isLoading?: boolean;
  error?: string;
  symbol: string;
}

export function MetricsDisplay({
  data,
  isLoading = false,
  error,
  symbol,
}: MetricsDisplayProps) {
  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-3">
        {[...Array(6)].map((_, i) => (
          <Card key={i}>
            <CardHeader>
              <Skeleton className="h-4 w-20" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-8 w-24" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Metrics</CardTitle>
          <CardDescription>Aggregated statistics for {symbol}</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">{error}</p>
        </CardContent>
      </Card>
    );
  }

  if (!data) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Metrics</CardTitle>
          <CardDescription>Aggregated statistics for {symbol}</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No metrics data available
          </p>
        </CardContent>
      </Card>
    );
  }

  const metrics = [
    {
      title: 'Average Price',
      value: formatPrice(data.averagePrice),
      icon: DollarSign,
      description: 'Mean price',
    },
    {
      title: 'High',
      value: formatPrice(data.high),
      icon: TrendingUp,
      description: 'Highest price',
      color: 'text-green-600 dark:text-green-400',
    },
    {
      title: 'Low',
      value: formatPrice(data.low),
      icon: TrendingDown,
      description: 'Lowest price',
      color: 'text-red-600 dark:text-red-400',
    },
    {
      title: 'Volatility',
      value: data.priceVolatility > 0 
        ? formatPrice(data.priceVolatility)
        : '$0',
      icon: Activity,
      description: 'Price std dev',
    },
    {
      title: 'Total Volume',
      value: `${formatNumber(data.totalVolume / 1000000)}M`,
      icon: DollarSign,
      description: 'Aggregated volume',
    },
    {
      title: 'Trade Count',
      value: data.tradeCount || '-',
      icon: Activity,
      description: 'Number of trades',
    },
  ];

  return (
    <div>
      <div className="mb-4">
        <h3 className="text-lg font-semibold">Metrics</h3>
        <p className="text-sm text-muted-foreground">
          Aggregated statistics for {symbol}
        </p>
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        {metrics.map((metric) => {
          const Icon = metric.icon;
          return (
            <Card key={metric.title}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  {metric.title}
                </CardTitle>
                <Icon className={`h-4 w-4 ${metric.color || 'text-muted-foreground'}`} />
              </CardHeader>
              <CardContent>
                <div className={`text-2xl font-bold ${metric.color || ''}`}>
                  {metric.value}
                </div>
                <p className="text-xs text-muted-foreground">
                  {metric.description}
                </p>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}



