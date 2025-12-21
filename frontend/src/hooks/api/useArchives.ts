/**
 * Archives API Hooks
 * React Query hooks for archive management
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';

interface Archive {
  id: string;
  status: 'completed' | 'processing' | 'failed';
  created_at: string;
  row_count?: number;
  file_size?: number;
  s3_path?: string;
  message?: string;
}

interface ArchiveStatusResponse {
  archive_id: string;
  status: string;
  created_at: string;
  row_count?: number;
  file_size?: number;
  s3_path?: string;
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
 * Download an archive
 * This returns a function that triggers the download
 */
export function useDownloadArchive() {
  return useMutation({
    mutationFn: async (archiveId: string) => {
      // Get the archive details first
      const archive = await apiClient.get<Archive>(
        `/api/v1/storage/archives/${archiveId}/status`
      );
      
      if (!archive.s3_path) {
        throw new Error('Archive download URL not available');
      }
      
      // For now, return the S3 path. In production, you'd want a signed URL
      return archive.s3_path;
    },
  });
}
