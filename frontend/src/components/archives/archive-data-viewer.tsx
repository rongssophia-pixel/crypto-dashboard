'use client';

/**
 * Archive Data Viewer Component
 * Displays archive data in a paginated table with filtering
 */

import { useState } from 'react';
import { useArchiveData } from '@/hooks/api/useArchiveData';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Loader2, ChevronLeft, ChevronRight, Search } from 'lucide-react';

interface ArchiveDataViewerProps {
  archiveId: string;
}

export default function ArchiveDataViewer({ archiveId }: ArchiveDataViewerProps) {
  const [page, setPage] = useState(0);
  const [symbolFilter, setSymbolFilter] = useState('');
  const [appliedFilter, setAppliedFilter] = useState('');
  const pageSize = 50;

  const { data, isLoading, error } = useArchiveData({
    archiveId,
    limit: pageSize,
    offset: page * pageSize,
    symbols: appliedFilter ? [appliedFilter] : undefined,
  });

  const handleApplyFilter = () => {
    setAppliedFilter(symbolFilter);
    setPage(0); // Reset to first page when filtering
  };

  const handleClearFilter = () => {
    setSymbolFilter('');
    setAppliedFilter('');
    setPage(0);
  };

  const handleNextPage = () => {
    if (data && data.rows.length === pageSize) {
      setPage((p) => p + 1);
    }
  };

  const handlePrevPage = () => {
    setPage((p) => Math.max(0, p - 1));
  };

  const formatCellValue = (value: any): string => {
    if (value === null || value === undefined) return '-';
    if (typeof value === 'number') {
      // Format numbers with up to 8 decimal places for crypto precision
      return value.toLocaleString(undefined, {
        maximumFractionDigits: 8,
      });
    }
    return String(value);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Archive Data</CardTitle>
        <CardDescription>
          Browse and filter archived market data
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Filters */}
        <div className="flex gap-4 items-end">
          <div className="flex-1 max-w-xs">
            <Label htmlFor="symbol-filter">Filter by Symbol</Label>
            <div className="flex gap-2">
              <Input
                id="symbol-filter"
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

        {/* Data Table */}
        {isLoading ? (
          <div className="flex justify-center p-8">
            <Loader2 className="w-8 h-8 animate-spin text-primary" />
          </div>
        ) : error ? (
          <div className="p-8 text-center text-destructive">
            <p>Error loading archive data</p>
            <p className="text-sm text-muted-foreground mt-2">
              {error instanceof Error ? error.message : 'Unknown error'}
            </p>
          </div>
        ) : !data || data.rows.length === 0 ? (
          <div className="p-8 text-center text-muted-foreground">
            <p>No data found</p>
          </div>
        ) : (
          <>
            <div className="rounded-md border overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    {data.column_names.map((column) => (
                      <TableHead key={column} className="whitespace-nowrap">
                        {column}
                      </TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.rows.map((row, idx) => (
                    <TableRow key={idx}>
                      {data.column_names.map((column) => (
                        <TableCell key={column} className="font-mono text-xs">
                          {formatCellValue(row[column])}
                        </TableCell>
                      ))}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>

            {/* Pagination */}
            <div className="flex items-center justify-between">
              <div className="text-sm text-muted-foreground">
                Showing {page * pageSize + 1} to {page * pageSize + data.rows.length} of{' '}
                {data.total_count} rows
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handlePrevPage}
                  disabled={page === 0}
                >
                  <ChevronLeft className="w-4 h-4 mr-1" />
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleNextPage}
                  disabled={data.rows.length < pageSize}
                >
                  Next
                  <ChevronRight className="w-4 h-4 ml-1" />
                </Button>
              </div>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}

