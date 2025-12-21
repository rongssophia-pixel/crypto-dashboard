'use client';

/**
 * Latest Prices Widget
 * Displays real-time prices for tracked symbols
 */

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { ArrowUp, ArrowDown } from 'lucide-react';
import { formatDateTime } from '@/lib/time';

interface MarketData {
  symbol: string;
  price: number;
  change_24h?: number;
  volume_24h?: number;
  timestamp: string;
}

interface LatestPricesProps {
  data?: MarketData[];
  isLoading?: boolean;
  error?: string;
}

export function LatestPrices({ data = [], isLoading = false, error }: LatestPricesProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Latest Prices</CardTitle>
          <CardDescription>Real-time market data</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="flex items-center justify-between py-2">
                <Skeleton className="h-4 w-20" />
                <Skeleton className="h-4 w-16" />
                <Skeleton className="h-4 w-16" />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Latest Prices</CardTitle>
          <CardDescription>Real-time market data</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">{error}</p>
        </CardContent>
      </Card>
    );
  }

  if (!data.length) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Latest Prices</CardTitle>
          <CardDescription>Real-time market data</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No market data available. Start a stream to see live prices.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Latest Prices</CardTitle>
        <CardDescription>Real-time market data for tracked symbols</CardDescription>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Symbol</TableHead>
              <TableHead className="text-right">Price</TableHead>
              <TableHead className="text-right">24h Change</TableHead>
              <TableHead className="text-right">Volume</TableHead>
              <TableHead className="text-right">Updated</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.map((item) => {
              const isPositive = (item.change_24h || 0) >= 0;
              return (
                <TableRow key={item.symbol} className="cursor-pointer hover:bg-muted/50">
                  <TableCell className="font-medium">{item.symbol}</TableCell>
                  <TableCell className="text-right font-mono">
                    ${item.price.toFixed(2)}
                  </TableCell>
                  <TableCell className="text-right">
                    {item.change_24h !== undefined ? (
                      <Badge
                        variant={isPositive ? 'default' : 'destructive'}
                        className="gap-1"
                      >
                        {isPositive ? (
                          <ArrowUp className="h-3 w-3" />
                        ) : (
                          <ArrowDown className="h-3 w-3" />
                        )}
                        {Math.abs(item.change_24h).toFixed(2)}%
                      </Badge>
                    ) : (
                      <span className="text-muted-foreground">-</span>
                    )}
                  </TableCell>
                  <TableCell className="text-right font-mono">
                    {item.volume_24h
                      ? `$${(item.volume_24h / 1000000).toFixed(2)}M`
                      : '-'}
                  </TableCell>
                  <TableCell className="text-right text-sm text-muted-foreground">
                    {formatDateTime(item.timestamp, 'HH:mm:ss')}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
