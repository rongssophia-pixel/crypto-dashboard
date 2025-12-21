'use client';

/**
 * Archive Management Component
 * Manage data archival to S3
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
import { Database, Download, Plus } from 'lucide-react';
import { formatDateTime } from '@/lib/time';
import { toast } from 'sonner';

interface Archive {
  id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  created_at: string;
  row_count?: number;
  file_size?: number;
}

interface ArchiveManagementProps {
  archives?: Archive[];
  isLoading?: boolean;
  onCreateArchive?: () => Promise<void>;
  onDownload?: (id: string) => void;
}

export function ArchiveManagement({
  archives = [],
  isLoading = false,
  onCreateArchive,
  onDownload,
}: ArchiveManagementProps) {
  const [isCreating, setIsCreating] = useState(false);

  const handleCreateArchive = async () => {
    setIsCreating(true);
    try {
      if (onCreateArchive) {
        await onCreateArchive();
        toast.success('Archive job started');
      }
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to create archive');
    } finally {
      setIsCreating(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return <Badge className="bg-green-600">Completed</Badge>;
      case 'processing':
        return <Badge className="bg-blue-600">Processing</Badge>;
      case 'pending':
        return <Badge variant="secondary">Pending</Badge>;
      case 'failed':
        return <Badge variant="destructive">Failed</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return '-';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Archive Management</CardTitle>
            <CardDescription>
              S3 archival and data exports • {archives.length} archives
            </CardDescription>
          </div>
          <Button onClick={handleCreateArchive} disabled={isCreating}>
            <Plus className="h-4 w-4 mr-2" />
            {isCreating ? 'Creating...' : 'New Archive'}
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {archives.length === 0 ? (
          <div className="text-center py-12">
            <Database className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <p className="text-muted-foreground">
              No archives yet. Click "New Archive" to create one.
            </p>
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Archive ID</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Created</TableHead>
                <TableHead className="text-right">Rows</TableHead>
                <TableHead className="text-right">Size</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {archives.map((archive) => (
                <TableRow key={archive.id}>
                  <TableCell className="font-mono text-sm">
                    {archive.id.substring(0, 8)}...
                  </TableCell>
                  <TableCell>{getStatusBadge(archive.status)}</TableCell>
                  <TableCell>
                    {formatDateTime(archive.created_at, 'MMM dd, HH:mm')}
                  </TableCell>
                  <TableCell className="text-right font-mono">
                    {archive.row_count?.toLocaleString() || '-'}
                  </TableCell>
                  <TableCell className="text-right font-mono">
                    {formatFileSize(archive.file_size)}
                  </TableCell>
                  <TableCell className="text-right">
                    {archive.status === 'completed' && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => onDownload && onDownload(archive.id)}
                      >
                        <Download className="h-3 w-3 mr-2" />
                        Download
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
