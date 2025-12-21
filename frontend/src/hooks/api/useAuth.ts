/**
 * Auth API Hooks
 * Additional auth-related hooks beyond the main useAuth context hook
 */

import { useQuery, useMutation } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';

interface User {
  id: string;
  email: string;
  username: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
}

interface UserResponse {
  user: User;
}

interface VerifyEmailResponse {
  message: string;
}

interface ForgotPasswordResponse {
  message: string;
}

interface ResetPasswordParams {
  token: string;
  new_password: string;
}

interface ResetPasswordResponse {
  message: string;
}

/**
 * Get current user info
 */
export function useCurrentUser() {
  return useQuery<UserResponse>({
    queryKey: ['current-user'],
    queryFn: async () => {
      return apiClient.get<UserResponse>('/api/v1/auth/me');
    },
    retry: 1,
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}

/**
 * Verify email mutation
 */
export function useVerifyEmail() {
  return useMutation<VerifyEmailResponse, Error, string>({
    mutationFn: async (token: string) => {
      return apiClient.post<VerifyEmailResponse>('/api/v1/auth/verify-email', { token });
    },
  });
}

/**
 * Request password reset
 */
export function useForgotPassword() {
  return useMutation<ForgotPasswordResponse, Error, string>({
    mutationFn: async (email: string) => {
      return apiClient.post<ForgotPasswordResponse>('/api/v1/auth/forgot-password', { email });
    },
  });
}

/**
 * Reset password with token
 */
export function useResetPassword() {
  return useMutation<ResetPasswordResponse, Error, ResetPasswordParams>({
    mutationFn: async (params: ResetPasswordParams) => {
      return apiClient.post<ResetPasswordResponse>('/api/v1/auth/reset-password', params);
    },
  });
}
