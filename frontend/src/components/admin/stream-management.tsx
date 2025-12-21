'use client';

/**
 * Stream Management Component
 * Manage data ingestion streams
 */

import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Play, Square, Plus, Activity, CheckCircle2, XCircle } from 'lucide-react';
import { toast } from 'sonner';

interface Stream {
  id: string;
  symbols: string[];
  status: 'running' | 'stopped' | 'error';
  event_count: number;
  started_at?: string;
}

interface StreamManagementProps {
  streams?: Stream[];
  isLoading?: boolean;
  onStartStream?: (symbols: string[]) => Promise<void>;
  onStopStream?: (id: string) => Promise<void>;
}

export function StreamManagement({
  streams = [],
  isLoading = false,
  onStartStream,
  onStopStream,
}: StreamManagementProps) {
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [newSymbols, setNewSymbols] = useState('');
  const [isStarting, setIsStarting] = useState(false);

  const handleStartStream = async () => {
    const symbols = newSymbols
      .split(',')
      .map((s) => s.trim().toUpperCase())
      .filter((s) => s.length > 0);

    if (symbols.length === 0) {
      toast.error('Please enter at least one symbol');
      return;
    }

    setIsStarting(true);
    try {
      if (onStartStream) {
        await onStartStream(symbols);
        toast.success('Stream started successfully');
        setIsDialogOpen(false);
        setNewSymbols('');
      }
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to start stream');
    } finally {
      setIsStarting(false);
    }
  };

  const handleStopStream = async (id: string) => {
    try {
      if (onStopStream) {
        await onStopStream(id);
        toast.success('Stream stopped successfully');
      }
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to stop stream');
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'running':
        return (
          <Badge className="gap-1 bg-green-600">
            <CheckCircle2 className="h-3 w-3" />
            Running
          </Badge>
        );
      case 'stopped':
        return (
          <Badge variant="secondary" className="gap-1">
            <Square className="h-3 w-3" />
            Stopped
          </Badge>
        );
      case 'error':
        return (
          <Badge variant="destructive" className="gap-1">
            <XCircle className="h-3 w-3" />
            Error
          </Badge>
        );
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Stream Management</CardTitle>
            <CardDescription>
              Manage data ingestion streams • {streams.length} active
            </CardDescription>
          </div>
          <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                Start Stream
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Start New Stream</DialogTitle>
                <DialogDescription>
                  Enter symbols to start streaming market data
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="symbols">Symbols (comma-separated)</Label>
                  <Input
                    id="symbols"
                    placeholder="BTCUSDT, ETHUSDT, BNBUSDT"
                    value={newSymbols}
                    onChange={(e) => setNewSymbols(e.target.value)}
                  />
                  <p className="text-xs text-muted-foreground">
                    Example: BTCUSDT, ETHUSDT
                  </p>
                </div>
              </div>
              <DialogFooter>
                <Button
                  variant="outline"
                  onClick={() => setIsDialogOpen(false)}
                >
                  Cancel
                </Button>
                <Button onClick={handleStartStream} disabled={isStarting}>
                  {isStarting ? 'Starting...' : 'Start Stream'}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </CardHeader>
      <CardContent>
        {streams.length === 0 ? (
          <div className="text-center py-12">
            <Activity className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <p className="text-muted-foreground">
              No active streams. Click "Start Stream" to begin.
            </p>
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Stream ID</TableHead>
                <TableHead>Symbols</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Events</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {streams.map((stream) => (
                <TableRow key={stream.id}>
                  <TableCell className="font-mono text-sm">
                    {stream.id.substring(0, 8)}...
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-1">
                      {stream.symbols.map((symbol) => (
                        <Badge key={symbol} variant="outline" className="text-xs">
                          {symbol}
                        </Badge>
                      ))}
                    </div>
                  </TableCell>
                  <TableCell>{getStatusBadge(stream.status)}</TableCell>
                  <TableCell className="text-right font-mono">
                    {stream.event_count.toLocaleString()}
                  </TableCell>
                  <TableCell className="text-right">
                    {stream.status === 'running' ? (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleStopStream(stream.id)}
                      >
                        <Square className="h-3 w-3 mr-2" />
                        Stop
                      </Button>
                    ) : (
                      <Button
                        variant="outline"
                        size="sm"
                        disabled
                      >
                        <Play className="h-3 w-3 mr-2" />
                        Start
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}
