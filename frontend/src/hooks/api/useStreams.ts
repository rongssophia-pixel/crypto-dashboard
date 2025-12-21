/**
 * Stream Management API Hooks
 * React Query hooks for stream endpoints
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';

interface StartStreamParams {
  symbols: string[];
  stream_type?: string;
}

/**
 * Get user's streams
 */
export function useStreams() {
  return useQuery({
    queryKey: ['streams'],
    queryFn: async () => {
      return apiClient.get('/api/v1/ingestion/streams/mine');
    },
    refetchInterval: 5000, // Refetch every 5 seconds
  });
}

/**
 * Get stream status
 */
export function useStreamStatus(streamId: string) {
  return useQuery({
    queryKey: ['stream-status', streamId],
    queryFn: async () => {
      return apiClient.get(`/api/v1/ingestion/streams/${streamId}/status`);
    },
    enabled: !!streamId,
    refetchInterval: 3000, // Poll every 3 seconds
  });
}

/**
 * Start a new stream
 */
export function useStartStream() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (params: StartStreamParams) => {
      return apiClient.post('/api/v1/ingestion/streams/start', params);
    },
    onSuccess: () => {
      // Invalidate streams query to refetch
      queryClient.invalidateQueries({ queryKey: ['streams'] });
    },
  });
}

/**
 * Stop a stream
 */
export function useStopStream() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (streamId: string) => {
      return apiClient.post(`/api/v1/ingestion/streams/${streamId}/stop`);
    },
    onSuccess: () => {
      // Invalidate streams query to refetch
      queryClient.invalidateQueries({ queryKey: ['streams'] });
    },
  });
}
