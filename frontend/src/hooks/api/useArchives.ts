/**
 * Archives API Hooks
 * React Query hooks for archive management
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';

interface Archive {
  archive_id: string;
  status: 'completed' | 'processing' | 'failed' | 'pending' | 'running';
  created_at: string;
  records_count?: number;
  size_bytes?: number;
  s3_path?: string;
  data_type?: string;
}

interface ArchiveStatusResponse {
  archive_id: string;
  status: string;
  created_at: string;
  records_archived?: number;
  size_bytes?: number;
  s3_path?: string;
  error_message?: string;
  completed_at?: string;
}

interface CreateArchiveParams {
  start_time: string;
  end_time: string;
  data_type: string;
  symbols?: string[];
}

/**
 * Get list of archives
 */
export function useArchives(limit: number = 20) {
  return useQuery<Archive[]>({
    queryKey: ['archives', limit],
    queryFn: async () => {
      const response = await apiClient.get<{ archives: Archive[] }>(
        `/api/v1/storage/archives?limit=${limit}`
      );
      return response.archives || [];
    },
    refetchInterval: 10000, // Refetch every 10 seconds
  });
}

/**
 * Get archive status by ID
 */
export function useArchiveStatus(archiveId: string | null) {
  return useQuery<ArchiveStatusResponse>({
    queryKey: ['archive-status', archiveId],
    queryFn: async () => {
      if (!archiveId) throw new Error('Archive ID is required');
      return apiClient.get(`/api/v1/storage/archives/${archiveId}/status`);
    },
    enabled: !!archiveId,
    refetchInterval: 5000, // Poll every 5 seconds for status updates
  });
}

/**
 * Create a new archive
 */
export function useCreateArchive() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (params: CreateArchiveParams) => {
      return apiClient.post('/api/v1/storage/archive', params);
    },
    onSuccess: () => {
      // Invalidate archives list to refetch
      queryClient.invalidateQueries({ queryKey: ['archives'] });
    },
  });
}

/**
 * Download an archive (deprecated - feature removed)
 * Keeping for backward compatibility but not functional
 */
export function useDownloadArchive() {
  return useMutation({
    mutationFn: async (_archiveId: string) => {
      throw new Error('Download feature is not available');
    },
  });
}

// Export Archive type for use in other components
export type { Archive, ArchiveStatusResponse };



