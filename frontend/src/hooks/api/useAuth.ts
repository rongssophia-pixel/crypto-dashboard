/**
 * Auth API Hooks
 * Additional auth-related hooks beyond the main useAuth context hook
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';

/**
 * Get current user info
 */
export function useCurrentUser() {
  return useQuery({
    queryKey: ['current-user'],
    queryFn: async () => {
      return apiClient.get('/api/v1/auth/me');
    },
    retry: 1,
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}

/**
 * Verify email mutation
 */
export function useVerifyEmail() {
  return useMutation({
    mutationFn: async (token: string) => {
      return apiClient.post('/api/v1/auth/verify-email', { token });
    },
  });
}

/**
 * Request password reset
 */
export function useForgotPassword() {
  return useMutation({
    mutationFn: async (email: string) => {
      return apiClient.post('/api/v1/auth/forgot-password', { email });
    },
  });
}

/**
 * Reset password with token
 */
export function useResetPassword() {
  return useMutation({
    mutationFn: async (params: { token: string; new_password: string }) => {
      return apiClient.post('/api/v1/auth/reset-password', params);
    },
  });
}
