'use client';

/**
 * User Info Display Component
 * Shows current user information
 */

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { User, Mail, Shield, Calendar, CheckCircle2, XCircle } from 'lucide-react';

interface UserInfoProps {
  user?: {
    user_id: string;
    email: string;
    roles: string[];
    email_verified?: boolean;
    created_at?: string;
  };
  isLoading?: boolean;
}

export function UserInfo({ user, isLoading = false }: UserInfoProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Account Information</CardTitle>
          <CardDescription>Your account details</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="space-y-2">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-6 w-48" />
            </div>
          ))}
        </CardContent>
      </Card>
    );
  }

  if (!user) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Account Information</CardTitle>
          <CardDescription>Your account details</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Unable to load user information
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Account Information</CardTitle>
        <CardDescription>Your account details and status</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Email */}
        <div className="flex items-start gap-3">
          <Mail className="h-5 w-5 text-muted-foreground mt-0.5" />
          <div className="flex-1">
            <p className="text-sm font-medium text-muted-foreground">Email</p>
            <div className="flex items-center gap-2 mt-1">
              <p className="text-base font-medium">{user.email}</p>
              {user.email_verified ? (
                <Badge className="gap-1 bg-green-600">
                  <CheckCircle2 className="h-3 w-3" />
                  Verified
                </Badge>
              ) : (
                <Badge variant="secondary" className="gap-1">
                  <XCircle className="h-3 w-3" />
                  Unverified
                </Badge>
              )}
            </div>
          </div>
        </div>

        {/* User ID */}
        <div className="flex items-start gap-3">
          <User className="h-5 w-5 text-muted-foreground mt-0.5" />
          <div className="flex-1">
            <p className="text-sm font-medium text-muted-foreground">User ID</p>
            <p className="text-base font-mono font-medium mt-1">{user.user_id}</p>
          </div>
        </div>

        {/* Roles */}
        <div className="flex items-start gap-3">
          <Shield className="h-5 w-5 text-muted-foreground mt-0.5" />
          <div className="flex-1">
            <p className="text-sm font-medium text-muted-foreground">Roles</p>
            <div className="flex flex-wrap gap-2 mt-2">
              {user.roles.map((role) => (
                <Badge key={role} variant="outline">
                  {role}
                </Badge>
              ))}
            </div>
          </div>
        </div>

        {/* Created At */}
        {user.created_at && (
          <div className="flex items-start gap-3">
            <Calendar className="h-5 w-5 text-muted-foreground mt-0.5" />
            <div className="flex-1">
              <p className="text-sm font-medium text-muted-foreground">
                Account Created
              </p>
              <p className="text-base font-medium mt-1">
                {new Date(user.created_at).toLocaleDateString('en-US', {
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric',
                })}
              </p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}






