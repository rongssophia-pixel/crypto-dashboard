'use client';

/**
 * Profile Page
 * User profile and preferences
 */

import { useAuth } from '@/hooks/useAuth';
import { UserInfo } from '@/components/profile/user-info';
import { Preferences } from '@/components/profile/preferences';

export default function ProfilePage() {
  const { user } = useAuth();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Profile Settings</h1>
        <p className="text-muted-foreground">
          Manage your account and preferences
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <div className="space-y-6">
          <UserInfo user={user || undefined} />
          <Preferences />
        </div>
      </div>
    </div>
  );
}
