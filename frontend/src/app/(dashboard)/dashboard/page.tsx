'use client';

/**
 * Dashboard Page
 * Main overview page with watchlist, latest prices, and quick actions
 */

import { useMemo, useState } from 'react';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  horizontalListSortingStrategy,
} from '@dnd-kit/sortable';
import { LatestPrices } from '@/components/dashboard/latest-prices';
import { QuickActions } from '@/components/dashboard/quick-actions';
import { SortableWatchlistCard } from '@/components/watchlist/sortable-watchlist-card';
import { WatchlistManager } from '@/components/watchlist/watchlist-manager';
import { useLatestPrices } from '@/hooks/api/useAnalytics';
import { useWatchlist, useReorderWatchlist } from '@/hooks/api/useWatchlist';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogTrigger, DialogTitle } from '@/components/ui/dialog';
import { ScrollArea, ScrollBar } from '@/components/ui/scroll-area';
import { Plus, Settings } from 'lucide-react';

export default function DashboardPage() {
  const [isManageOpen, setIsManageOpen] = useState(false);

  // Fetch watchlist
  const { data: watchlistData } = useWatchlist();
  const watchlistSymbols = watchlistData?.symbols || [];
  
  // Reorder mutation
  const reorderMutation = useReorderWatchlist();

  // Fetch latest prices for watchlist symbols
  const { data: pricesResponse, isLoading: pricesLoading, error: pricesError } = useLatestPrices({
    symbols: watchlistSymbols,
  });

  // Transform prices data for LatestPrices component
  const latestPrices = useMemo(() => {
    return pricesResponse?.prices || [];
  }, [pricesResponse]);

  // DnD sensors
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  // Handle drag end
  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;

    if (over && active.id !== over.id) {
      const oldIndex = watchlistSymbols.indexOf(active.id as string);
      const newIndex = watchlistSymbols.indexOf(over.id as string);
      const newOrder = arrayMove(watchlistSymbols, oldIndex, newIndex);
      reorderMutation.mutate(newOrder);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          Overview of your crypto analytics platform
        </p>
      </div>

      {/* Watchlist Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold">My Watchlist</h2>
            <p className="text-sm text-muted-foreground">Drag to reorder</p>
          </div>
          <Dialog open={isManageOpen} onOpenChange={setIsManageOpen}>
            <DialogTrigger asChild>
              <Button variant="outline" size="sm">
                <Settings className="w-4 h-4 mr-2" />
                Manage
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl">
              <DialogTitle className="sr-only">Manage Watchlist</DialogTitle>
              <WatchlistManager />
            </DialogContent>
          </Dialog>
        </div>

        <ScrollArea className="w-full whitespace-nowrap rounded-md border bg-card/50 p-4">
          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragEnd={handleDragEnd}
          >
            <SortableContext
              items={watchlistSymbols}
              strategy={horizontalListSortingStrategy}
            >
              <div className="flex w-max space-x-4">
                {watchlistSymbols.map((symbol) => (
                  <div key={symbol} className="w-[280px] inline-block whitespace-normal align-top">
                    <SortableWatchlistCard symbol={symbol} />
                  </div>
                ))}
                {watchlistSymbols.length === 0 && (
                  <div className="flex items-center justify-center w-[280px] h-[140px] border border-dashed rounded-xl">
                    <Button variant="ghost" onClick={() => setIsManageOpen(true)}>
                      <Plus className="w-4 h-4 mr-2" />
                      Add Symbols
                    </Button>
                  </div>
                )}
              </div>
            </SortableContext>
          </DndContext>
          <ScrollBar orientation="horizontal" />
        </ScrollArea>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <LatestPrices 
          data={latestPrices} 
          isLoading={pricesLoading}
          error={pricesError?.message}
        />
        <QuickActions />
      </div>
    </div>
  );
}
