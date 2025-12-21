/**
 * Stream Management API Hooks
 * React Query hooks for stream endpoints
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';

interface Stream {
  stream_id?: string;
  id?: string;
  symbols?: string[];
  is_active: boolean;
  events_processed?: number;
  event_count?: number;
  started_at?: string;
  created_at?: string;
}

interface StreamsResponse {
  streams: Stream[];
}

interface StreamStatusResponse {
  stream_id: string;
  is_active: boolean;
  symbols: string[];
  events_processed: number;
  started_at?: string;
}

interface StartStreamParams {
  symbols: string[];
  stream_type?: string;
}

interface StartStreamResponse {
  stream_id: string;
  message: string;
}

interface StopStreamResponse {
  message: string;
}

/**
 * Get user's streams
 */
export function useStreams() {
  return useQuery<StreamsResponse>({
    queryKey: ['streams'],
    queryFn: async () => {
      return apiClient.get<StreamsResponse>('/api/v1/ingestion/streams/mine');
    },
    refetchInterval: 5000, // Refetch every 5 seconds
  });
}

/**
 * Get stream status
 */
export function useStreamStatus(streamId: string) {
  return useQuery<StreamStatusResponse>({
    queryKey: ['stream-status', streamId],
    queryFn: async () => {
      return apiClient.get<StreamStatusResponse>(`/api/v1/ingestion/streams/${streamId}/status`);
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

  return useMutation<StartStreamResponse, Error, StartStreamParams>({
    mutationFn: async (params: StartStreamParams) => {
      return apiClient.post<StartStreamResponse>('/api/v1/ingestion/streams/start', params);
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

  return useMutation<StopStreamResponse, Error, string>({
    mutationFn: async (streamId: string) => {
      return apiClient.post<StopStreamResponse>(`/api/v1/ingestion/streams/${streamId}/stop`);
    },
    onSuccess: () => {
      // Invalidate streams query to refetch
      queryClient.invalidateQueries({ queryKey: ['streams'] });
    },
  });
}
