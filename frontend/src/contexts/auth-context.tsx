'use client';

/**
 * Authentication Context
 * Manages user authentication state, tokens, and auth operations
 */

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { apiClient, TokenResponse } from '@/lib/api-client';
import { useRouter } from 'next/navigation';

interface User {
  user_id: string;
  email: string;
  roles: string[];
  email_verified?: boolean;
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  // Fetch current user info
  const refreshUser = useCallback(async () => {
    try {
      const { accessToken } = apiClient.getTokens();
      if (!accessToken) {
        setUser(null);
        return;
      }

      const userData = await apiClient.get<User>('/api/v1/auth/me');
      setUser(userData);
    } catch (error) {
      console.error('Failed to fetch user:', error);
      setUser(null);
      apiClient.clearTokens();
    }
  }, []);

  // Initialize auth state on mount
  useEffect(() => {
    const initAuth = async () => {
      const { accessToken } = apiClient.getTokens();
      if (accessToken) {
        await refreshUser();
      }
      setIsLoading(false);
    };

    initAuth();
  }, [refreshUser]);

  // Setup token refresh timer (refresh 5 minutes before expiration)
  useEffect(() => {
    if (!user) return;

    const refreshInterval = setInterval(
      async () => {
        try {
          const { refreshToken } = apiClient.getTokens();
          if (refreshToken) {
            await apiClient.post<TokenResponse>('/api/v1/auth/refresh', {
              refresh_token: refreshToken,
            });
          }
        } catch (error) {
          console.error('Token refresh failed:', error);
          setUser(null);
          apiClient.clearTokens();
          router.push('/login');
        }
      },
      55 * 60 * 1000
    ); // 55 minutes (tokens expire in 60)

    return () => clearInterval(refreshInterval);
  }, [user, router]);

  const login = async (email: string, password: string) => {
    try {
      const response = await apiClient.post<TokenResponse>(
        '/api/v1/auth/login',
        { email, password }
      );
      
      apiClient.setTokens(response.access_token, response.refresh_token);
      await refreshUser();
      router.push('/dashboard');
    } catch (error) {
      throw error;
    }
  };

  const register = async (email: string, password: string) => {
    try {
      const response = await apiClient.post<TokenResponse>(
        '/api/v1/auth/register',
        { email, password }
      );
      
      apiClient.setTokens(response.access_token, response.refresh_token);
      await refreshUser();
      router.push('/dashboard');
    } catch (error) {
      throw error;
    }
  };

  const logout = async () => {
    try {
      const { refreshToken } = apiClient.getTokens();
      if (refreshToken) {
        await apiClient.post('/api/v1/auth/logout', {
          refresh_token: refreshToken,
        });
      }
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      apiClient.clearTokens();
      setUser(null);
      router.push('/login');
    }
  };

  const value: AuthContextType = {
    user,
    isLoading,
    isAuthenticated: !!user,
    login,
    register,
    logout,
    refreshUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}






