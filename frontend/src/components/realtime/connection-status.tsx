'use client';

/**
 * Connection Status Component
 * Displays WebSocket connection status and subscription info
 */

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Wifi, WifiOff, Loader2, RefreshCw } from 'lucide-react';
import { ConnectionStatus as Status } from '@/lib/websocket-manager';

interface ConnectionStatusProps {
  status: Status;
  subscriptions: string[];
  onReconnect?: () => void;
}

export function ConnectionStatus({
  status,
  subscriptions,
  onReconnect,
}: ConnectionStatusProps) {
  const getStatusInfo = (status: Status) => {
    switch (status) {
      case 'connected':
        return {
          label: 'Connected',
          variant: 'default' as const,
          icon: <Wifi className="h-4 w-4" />,
          color: 'text-green-600 dark:text-green-400',
        };
      case 'connecting':
        return {
          label: 'Connecting...',
          variant: 'secondary' as const,
          icon: <Loader2 className="h-4 w-4 animate-spin" />,
          color: 'text-blue-600 dark:text-blue-400',
        };
      case 'reconnecting':
        return {
          label: 'Reconnecting...',
          variant: 'secondary' as const,
          icon: <Loader2 className="h-4 w-4 animate-spin" />,
          color: 'text-yellow-600 dark:text-yellow-400',
        };
      case 'disconnected':
        return {
          label: 'Disconnected',
          variant: 'destructive' as const,
          icon: <WifiOff className="h-4 w-4" />,
          color: 'text-red-600 dark:text-red-400',
        };
    }
  };

  const statusInfo = getStatusInfo(status);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-lg">Connection Status</CardTitle>
            <CardDescription>WebSocket stream information</CardDescription>
          </div>
          {status === 'disconnected' && onReconnect && (
            <Button variant="outline" size="sm" onClick={onReconnect}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Reconnect
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center gap-3">
          <div className={statusInfo.color}>{statusInfo.icon}</div>
          <div>
            <Badge variant={statusInfo.variant} className="gap-1">
              {statusInfo.label}
            </Badge>
          </div>
        </div>

        <div>
          <p className="text-sm font-medium mb-2">Active Subscriptions</p>
          {subscriptions.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No active subscriptions
            </p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {subscriptions.map((symbol) => (
                <Badge key={symbol} variant="outline">
                  {symbol}
                </Badge>
              ))}
            </div>
          )}
          <p className="text-xs text-muted-foreground mt-2">
            {subscriptions.length} / 50 symbols
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
