/**
 * Watchlist API Hooks
 * React Query hooks for watchlist operations
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';

// Types
export interface WatchlistResponse {
  symbols: string[];
}

interface WatchlistAddRequest {
  symbol: string;
}

interface MessageResponse {
  message: string;
  success: boolean;
}

/**
 * Get user's watchlist
 */
export function useWatchlist() {
  return useQuery<WatchlistResponse>({
    queryKey: ['watchlist'],
    queryFn: async () => {
      return apiClient.get<WatchlistResponse>('/api/v1/watchlist');
    },
  });
}

/**
 * Add symbol to watchlist
 */
export function useAddToWatchlist() {
  const queryClient = useQueryClient();

  return useMutation<MessageResponse, Error, WatchlistAddRequest>({
    mutationFn: async (data) => {
      return apiClient.post<MessageResponse>('/api/v1/watchlist', data);
    },
    onSuccess: () => {
      // Invalidate watchlist query to refetch
      queryClient.invalidateQueries({ queryKey: ['watchlist'] });
    },
  });
}

/**
 * Remove symbol from watchlist
 */
export function useRemoveFromWatchlist() {
  const queryClient = useQueryClient();

  return useMutation<MessageResponse, Error, string>({
    mutationFn: async (symbol) => {
      return apiClient.delete<MessageResponse>(`/api/v1/watchlist/${symbol}`);
    },
    onSuccess: () => {
      // Invalidate watchlist query to refetch
      queryClient.invalidateQueries({ queryKey: ['watchlist'] });
    },
  });
}

/**
 * Reorder watchlist (optimistic update, client-side only for now)
 */
export function useReorderWatchlist() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, string[]>({
    mutationFn: async (newOrder) => {
      // For now, this is a client-side only operation
      // In the future, you could add an API endpoint to persist the order
      // e.g., return apiClient.put('/api/v1/watchlist/order', { symbols: newOrder });
      return Promise.resolve();
    },
    onMutate: async (newOrder) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: ['watchlist'] });

      // Snapshot the previous value
      const previousWatchlist = queryClient.getQueryData<WatchlistResponse>(['watchlist']);

      // Optimistically update to the new value
      queryClient.setQueryData<WatchlistResponse>(['watchlist'], {
        symbols: newOrder,
      });

      // Return a context object with the snapshotted value
      return { previousWatchlist };
    },
    onError: (_err, _newOrder, context) => {
      // If the mutation fails, use the context returned from onMutate to roll back
      if (context?.previousWatchlist) {
        queryClient.setQueryData(['watchlist'], context.previousWatchlist);
      }
    },
  });
}
