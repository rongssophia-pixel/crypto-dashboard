/**
 * System API Hooks
 * React Query hooks for system health and dashboard statistics
 */

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';

interface HealthResponse {
  status: string;
  services: {
    ingestion?: string;
    analytics?: string;
    storage?: string;
    notification?: string;
  };
}

interface ServiceStatus {
  name: string;
  status: 'healthy' | 'degraded' | 'down' | 'unknown';
  message?: string;
}

/**
 * Get system health
 * Polls the /health endpoint every 5 seconds
 */
export function useSystemHealth() {
  return useQuery<ServiceStatus[]>({
    queryKey: ['system-health'],
    queryFn: async () => {
      const response = await apiClient.get<HealthResponse>('/health');
      
      // Transform backend response to ServiceStatus format
      const services: ServiceStatus[] = [];
      
      // Map backend service statuses
      if (response.services) {
        Object.entries(response.services).forEach(([name, status]) => {
          let mappedStatus: 'healthy' | 'degraded' | 'down' | 'unknown' = 'unknown';
          
          if (status === 'healthy' || status === 'running') {
            mappedStatus = 'healthy';
          } else if (status === 'degraded') {
            mappedStatus = 'degraded';
          } else if (status === 'down' || status === 'error') {
            mappedStatus = 'down';
          }
          
          services.push({
            name: name.charAt(0).toUpperCase() + name.slice(1) + ' Service',
            status: mappedStatus,
          });
        });
      }
      
      // Add infrastructure services with unknown status (backend doesn't report these yet)
      const infraServices = ['PostgreSQL', 'ClickHouse', 'Kafka', 'WebSocket'];
      infraServices.forEach(name => {
        services.push({
          name,
          status: 'unknown',
        });
      });
      
      return services;
    },
    refetchInterval: 5000, // Poll every 5 seconds
    retry: 1,
  });
}

interface DashboardStatsResponse {
  service: string;
  status: string;
  version: string;
}

/**
 * Get dashboard statistics
 * Fetches aggregated stats for the dashboard overview
 */
export function useDashboardStats() {
  return useQuery<DashboardStatsResponse>({
    queryKey: ['dashboard-stats'],
    queryFn: async () => {
      // Fetch from root endpoint which includes service info
      const response = await apiClient.get<{
        service?: string;
        status?: string;
        version?: string;
      }>('/');
      
      return {
        service: response.service || 'API Gateway',
        status: response.status || 'running',
        version: response.version || '1.0.0',
      };
    },
    refetchInterval: 10000, // Refetch every 10 seconds
  });
}


