'use client';

/**
 * Watchlist Manager Component
 * Allows adding/removing symbols from watchlist
 */

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useWatchlist, useAddToWatchlist, useRemoveFromWatchlist } from '@/hooks/api/useWatchlist';
import { useAvailableSymbols } from '@/hooks/api/useIngestion';
import { Loader2, Plus, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

export function WatchlistManager() {
  const [selectedSymbol, setSelectedSymbol] = useState('');
  const { data, isLoading } = useWatchlist();
  const { data: symbolsData, isLoading: isLoadingSymbols } = useAvailableSymbols();
  const addMutation = useAddToWatchlist();
  const removeMutation = useRemoveFromWatchlist();

  const watchlistSymbols = data?.symbols || [];
  const allSymbols = symbolsData?.symbols || [];
  
  // Filter out symbols already in watchlist
  const availableToAdd = allSymbols.filter(
    (symbol) => !watchlistSymbols.includes(symbol)
  );

  const handleAdd = () => {
    if (!selectedSymbol) return;
    
    addMutation.mutate({ symbol: selectedSymbol }, {
      onSuccess: (response) => {
        if (response.success) {
          toast.success(response.message);
          setSelectedSymbol('');
        } else {
          toast.info(response.message);
        }
      },
      onError: () => {
        toast.error('Failed to add symbol');
      },
    });
  };

  const handleRemove = (symbol: string) => {
    removeMutation.mutate(symbol, {
      onSuccess: () => {
        toast.success(`Removed ${symbol} from watchlist`);
      },
      onError: () => {
        toast.error(`Failed to remove ${symbol}`);
      },
    });
  };

  const isLoadingData = isLoading || isLoadingSymbols;

  return (
    <Card className="border-0 shadow-none">
      <CardHeader className="px-0 pt-0">
        <CardTitle>Manage Watchlist</CardTitle>
        <CardDescription>
          Add or remove symbols from your personal watchlist
        </CardDescription>
      </CardHeader>
      <CardContent className="px-0 pb-0">
        <div className="flex gap-2 mb-6">
          <Select 
            value={selectedSymbol} 
            onValueChange={setSelectedSymbol}
            disabled={isLoadingSymbols || availableToAdd.length === 0}
          >
            <SelectTrigger className="w-full max-w-xs">
              <SelectValue placeholder={
                isLoadingSymbols 
                  ? "Loading symbols..." 
                  : availableToAdd.length === 0 
                  ? "All symbols added" 
                  : "Select a symbol to add"
              } />
            </SelectTrigger>
            <SelectContent>
              {availableToAdd.length === 0 ? (
                <SelectItem value="_none" disabled>
                  All symbols added
                </SelectItem>
              ) : (
                availableToAdd.map((symbol) => (
                  <SelectItem key={symbol} value={symbol}>
                    {symbol}
                  </SelectItem>
                ))
              )}
            </SelectContent>
          </Select>
          <Button 
            onClick={handleAdd} 
            disabled={addMutation.isPending || !selectedSymbol || isLoadingSymbols}
          >
            {addMutation.isPending ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <Plus className="w-4 h-4 mr-2" />
            )}
            Add
          </Button>
        </div>

        {isLoadingData ? (
          <div className="flex justify-center p-4">
            <Loader2 className="w-6 h-6 animate-spin" />
          </div>
        ) : (
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Symbol</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {watchlistSymbols.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={2} className="text-center h-24 text-muted-foreground">
                      No symbols in watchlist
                    </TableCell>
                  </TableRow>
                ) : (
                  watchlistSymbols.map((symbol) => (
                    <TableRow key={symbol}>
                      <TableCell className="font-medium">{symbol}</TableCell>
                      <TableCell className="text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleRemove(symbol)}
                          disabled={removeMutation.isPending}
                        >
                          <Trash2 className="w-4 h-4 text-destructive" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
