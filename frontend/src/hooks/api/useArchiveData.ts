/**
 * Archive Data API Hooks
 * React Query hooks for querying archive data
 */

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';

interface ArchiveDataRow {
  [key: string]: string | number | null;
}

interface ArchiveDataResponse {
  rows: ArchiveDataRow[];
  column_names: string[];
  total_count: number;
}

interface QueryArchiveDataParams {
  archiveId: string;
  limit?: number;
  offset?: number;
  symbols?: string[];
  startTime?: string;
  endTime?: string;
}

/**
 * Query archive data with pagination and filtering
 */
export function useArchiveData({
  archiveId,
  limit = 100,
  offset = 0,
  symbols,
  startTime,
  endTime,
}: QueryArchiveDataParams) {
  return useQuery<ArchiveDataResponse>({
    queryKey: ['archive-data', archiveId, limit, offset, symbols, startTime, endTime],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.append('limit', limit.toString());
      params.append('offset', offset.toString());
      
      if (symbols && symbols.length > 0) {
        symbols.forEach(symbol => params.append('symbols', symbol));
      }
      
      if (startTime) {
        params.append('start_time', startTime);
      }
      
      if (endTime) {
        params.append('end_time', endTime);
      }

      const response = await apiClient.get<ArchiveDataResponse>(
        `/api/v1/storage/archives/${archiveId}/data?${params.toString()}`
      );
      
      return response;
    },
    enabled: !!archiveId,
    staleTime: 60000, // Data is relatively static, cache for 1 minute
  });
}

export type { ArchiveDataRow, ArchiveDataResponse };





