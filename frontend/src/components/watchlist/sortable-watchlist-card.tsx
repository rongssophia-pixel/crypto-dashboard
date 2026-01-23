'use client';

/**
 * Sortable Watchlist Card Component
 * Draggable wrapper for WatchlistCard
 */

import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { WatchlistCard } from './watchlist-card';
import { GripVertical } from 'lucide-react';

interface SortableWatchlistCardProps {
  symbol: string;
}

export function SortableWatchlistCard({ symbol }: SortableWatchlistCardProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: symbol });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="relative group/sortable"
    >
      {/* Drag Handle */}
      <div
        {...attributes}
        {...listeners}
        className="absolute left-2 top-1/2 -translate-y-1/2 z-10 p-1 rounded cursor-grab active:cursor-grabbing opacity-0 group-hover/sortable:opacity-100 transition-opacity bg-background/80 backdrop-blur-sm"
      >
        <GripVertical className="w-4 h-4 text-muted-foreground" />
      </div>
      <WatchlistCard symbol={symbol} />
    </div>
  );
}

