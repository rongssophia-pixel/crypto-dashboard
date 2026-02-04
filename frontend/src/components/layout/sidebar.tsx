'use client';

/**
 * Sidebar Navigation Component
 */

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  Home, 
  BarChart3, 
  User,
  LogOut,
  TrendingUp,
  Archive,
  Layers
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/hooks/useAuth';
import { cn } from '@/lib/utils';

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: Home },
  { name: 'Analytics', href: '/analytics', icon: BarChart3 },
  { name: 'Depth', href: '/depth', icon: Layers },
  { name: 'Archives', href: '/archives', icon: Archive },
  { name: 'Profile', href: '/profile', icon: User },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  return (
    <div className="flex flex-col h-full bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800">
      {/* Logo */}
      <div className="flex items-center gap-2 p-6 border-b border-slate-200 dark:border-slate-800">
        <TrendingUp className="h-8 w-8 text-blue-600" />
        <div>
          <h1 className="font-bold text-lg">Crypto Analytics</h1>
          <p className="text-xs text-slate-500">Market Data Platform</p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1">
        {navigation.map((item) => {
          const isActive = pathname === item.href || pathname?.startsWith(item.href + '/');
          const Icon = item.icon;
          
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                isActive
                  ? 'bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-400'
                  : 'text-slate-700 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800'
              )}
            >
              <Icon className="h-5 w-5" />
              {item.name}
            </Link>
          );
        })}
      </nav>

      {/* User Info & Logout */}
      <div className="p-4 border-t border-slate-200 dark:border-slate-800 space-y-2">
        <div className="px-3 py-2">
          <p className="text-sm font-medium text-slate-900 dark:text-slate-100 truncate">
            {user?.email}
          </p>
          <p className="text-xs text-slate-500">
            {user?.roles.join(', ')}
          </p>
        </div>
        <Button
          variant="ghost"
          className="w-full justify-start"
          onClick={() => logout()}
        >
          <LogOut className="h-4 w-4 mr-2" />
          Logout
        </Button>
      </div>
    </div>
  );
}
