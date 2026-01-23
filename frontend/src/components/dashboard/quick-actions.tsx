'use client';

/**
 * Quick Actions Panel
 * Quick access buttons for common tasks
 */

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { BarChart3, Activity, Archive } from 'lucide-react';
import Link from 'next/link';

export function QuickActions() {
  const actions = [
    {
      title: 'View Analytics',
      description: 'Explore charts and metrics',
      icon: BarChart3,
      href: '/analytics',
      variant: 'default' as const,
    },
    {
      title: 'View Archives',
      description: 'Download historical data',
      icon: Archive,
      href: '/archives',
      variant: 'outline' as const,
    },
    {
      title: 'Real-time Feed',
      description: 'Watch live market updates',
      icon: Activity,
      href: '/analytics#market-data',
      variant: 'outline' as const,
    },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Quick Actions</CardTitle>
        <CardDescription>Common tasks and shortcuts</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid gap-4">
          {actions.map((action) => {
            const Icon = action.icon;
            return (
              <Button
                key={action.title}
                variant={action.variant}
                className="h-auto flex-col items-start p-4 space-y-2"
                asChild
              >
                <Link href={action.href}>
                  <div className="flex items-center gap-2 w-full">
                    <Icon className="h-5 w-5" />
                    <span className="font-semibold">{action.title}</span>
                  </div>
                  <p className="text-xs text-left text-muted-foreground font-normal">
                    {action.description}
                  </p>
                </Link>
              </Button>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
