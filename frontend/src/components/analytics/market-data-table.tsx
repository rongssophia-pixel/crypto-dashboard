'use client';

/**
 * Market Data Table Component
 * Sortable, paginated table of market data
 */

import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { formatDateTime } from '@/lib/time';
import { formatPrice, formatNumber, formatPercentage } from '@/lib/utils';
import { Download } from 'lucide-react';

interface MarketDataRow {
  timestamp: string;
  symbol: string;
  price: number;
  volume: number;
  bid?: number;
  ask?: number;
  spread?: number;
}

interface MarketDataTableProps {
  data?: MarketDataRow[];
  isLoading?: boolean;
  error?: string;
}

export function MarketDataTable({
  data = [],
  isLoading = false,
  error,
}: MarketDataTableProps) {
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;

  const handleExport = () => {
    if (!data.length) return;

    // Simple CSV export
    const headers = ['Timestamp', 'Symbol', 'Price', 'Volume', 'Bid', 'Ask', 'Spread'];
    const rows = data.map((row) => [
      row.timestamp,
      row.symbol,
      row.price,
      row.volume,
      row.bid || '',
      row.ask || '',
      row.spread || '',
    ]);

    const csv = [headers, ...rows].map((row) => row.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `market-data-${new Date().toISOString()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Market Data</CardTitle>
          <CardDescription>Historical price data</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {[...Array(5)].map((_, i) => (
              <Skeleton key={i} className="h-12 w-full" />
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
          <CardTitle>Market Data</CardTitle>
          <CardDescription>Historical price data</CardDescription>
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
          <CardTitle>Market Data</CardTitle>
          <CardDescription>Historical price data</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No data available for the selected filters
          </p>
        </CardContent>
      </Card>
    );
  }

  // Pagination
  const totalPages = Math.ceil(data.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const currentData = data.slice(startIndex, endIndex);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Market Data</CardTitle>
            <CardDescription>
              Showing {startIndex + 1}-{Math.min(endIndex, data.length)} of {data.length} records
            </CardDescription>
          </div>
          <Button variant="outline" size="sm" onClick={handleExport}>
            <Download className="h-4 w-4 mr-2" />
            Export CSV
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Timestamp</TableHead>
                <TableHead>Symbol</TableHead>
                <TableHead className="text-right">Price</TableHead>
                <TableHead className="text-right">Volume</TableHead>
                <TableHead className="text-right">Bid</TableHead>
                <TableHead className="text-right">Ask</TableHead>
                <TableHead className="text-right">Spread</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {currentData.map((row, index) => (
                <TableRow key={index}>
                  <TableCell className="text-sm">
                    {formatDateTime(row.timestamp, 'MMM dd, HH:mm:ss')}
                  </TableCell>
                  <TableCell className="font-medium">{row.symbol}</TableCell>
                  <TableCell className="text-right font-mono">
                    {formatPrice(row.price)}
                  </TableCell>
                  <TableCell className="text-right font-mono">
                    {formatNumber(row.volume / 1000)}K
                  </TableCell>
                  <TableCell className="text-right font-mono">
                    {row.bid ? formatPrice(row.bid) : '-'}
                  </TableCell>
                  <TableCell className="text-right font-mono">
                    {row.ask ? formatPrice(row.ask) : '-'}
                  </TableCell>
                  <TableCell className="text-right font-mono">
                    {row.spread !== undefined ? formatPercentage(row.spread, 2) : '-'}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between mt-4">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setCurrentPage(currentPage - 1)}
              disabled={currentPage === 1}
            >
              Previous
            </Button>
            <span className="text-sm text-muted-foreground">
              Page {currentPage} of {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setCurrentPage(currentPage + 1)}
              disabled={currentPage === totalPages}
            >
              Next
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}



