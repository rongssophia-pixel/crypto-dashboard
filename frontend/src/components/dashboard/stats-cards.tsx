'use client';

/**
 * Stats Cards Component
 * Displays key metrics on the dashboard
 */

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { TrendingUp, Activity, Clock, BarChart3 } from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';

interface StatsCardsProps {
  symbolsCount?: number;
  activeStreams?: number;
  lastUpdate?: string;
  volume24h?: string;
  isLoading?: boolean;
}

export function StatsCards({
  symbolsCount = 0,
  activeStreams = 0,
  lastUpdate,
  volume24h,
  isLoading = false,
}: StatsCardsProps) {
  const stats = [
    {
      title: 'Symbols Tracked',
      value: symbolsCount,
      icon: TrendingUp,
      description: 'Total cryptocurrencies',
    },
    {
      title: 'Active Streams',
      value: activeStreams,
      icon: Activity,
      description: 'Real-time data feeds',
    },
    {
      title: 'Last Update',
      value: lastUpdate || 'N/A',
      icon: Clock,
      description: 'Most recent data',
    },
    {
      title: '24h Volume',
      value: volume24h || 'N/A',
      icon: BarChart3,
      description: 'Aggregated volume',
    },
  ];

  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((_stat, i) => (
          <Card key={i}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                <Skeleton className="h-4 w-24" />
              </CardTitle>
              <Skeleton className="h-4 w-4 rounded" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-8 w-16 mb-1" />
              <Skeleton className="h-3 w-32" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      {stats.map((stat) => {
        const Icon = stat.icon;
        return (
          <Card key={stat.title}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                {stat.title}
              </CardTitle>
              <Icon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stat.value}</div>
              <p className="text-xs text-muted-foreground">
                {stat.description}
              </p>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
