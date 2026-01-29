'use client';

/**
 * Archives Page
 * List and manage data archives
 */

import { useArchives } from '@/hooks/api/useArchives';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Eye, Loader2, FileArchive } from 'lucide-react';
import { format } from 'date-fns';
import { useRouter } from 'next/navigation';
import { formatNumber } from '@/lib/utils';

export default function ArchivesPage() {
  const { data: archives, isLoading } = useArchives();
  const router = useRouter();

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return 'N/A';
    const units = ['B', 'KB', 'MB', 'GB'];
    let size = bytes;
    let unitIndex = 0;
    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024;
      unitIndex++;
    }
    return `${formatNumber(size)} ${units[unitIndex]}`;
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'default'; // primary/black
      case 'running':
      case 'processing':
        return 'secondary'; // gray
      case 'failed':
        return 'destructive'; // red
      case 'pending':
        return 'outline';
      default:
        return 'outline';
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Archives</h1>
        <p className="text-muted-foreground">
          View and explore historical market data archives
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Data Archives</CardTitle>
          <CardDescription>
            View and query generated historical data files
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center p-8">
              <Loader2 className="w-8 h-8 animate-spin text-primary" />
            </div>
          ) : !archives || archives.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center text-muted-foreground">
              <FileArchive className="w-12 h-12 mb-4 opacity-50" />
              <p>No archives found</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Archive ID</TableHead>
                  <TableHead>Created At</TableHead>
                  <TableHead>Rows</TableHead>
                  <TableHead>Size</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {archives.map((archive) => (
                  <TableRow key={archive.archive_id}>
                    <TableCell className="font-mono text-xs">{archive.archive_id}</TableCell>
                    <TableCell>
                      {format(new Date(archive.created_at), 'MMM d, yyyy HH:mm')}
                    </TableCell>
                    <TableCell>{archive.records_count?.toLocaleString() || '-'}</TableCell>
                    <TableCell>{formatFileSize(archive.size_bytes)}</TableCell>
                    <TableCell>
                      <Badge variant={getStatusColor(archive.status) as any}>
                        {archive.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      {archive.status === 'completed' && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => router.push(`/archives/${archive.archive_id}`)}
                        >
                          <Eye className="w-4 h-4 mr-2" />
                          View
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
    </div>
  );
}

