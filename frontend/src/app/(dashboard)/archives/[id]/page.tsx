'use client';

/**
 * Archive Detail Page
 * View and visualize specific archive data
 */

import { useParams } from 'next/navigation';
import { useState } from 'react';
import { useArchiveStatus } from '@/hooks/api/useArchives';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Loader2, ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import Link from 'next/link';
import { format } from 'date-fns';
import ArchiveDataViewer from '@/components/archives/archive-data-viewer';
import ArchiveChart from '@/components/archives/archive-chart';

export default function ArchiveDetailPage() {
  const params = useParams();
  const archiveId = params.id as string;
  const [activeTab, setActiveTab] = useState('data');

  const { data: archive, isLoading, error } = useArchiveStatus(archiveId);

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return 'N/A';
    const units = ['B', 'KB', 'MB', 'GB'];
    let size = bytes;
    let unitIndex = 0;
    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024;
      unitIndex++;
    }
    return `${size.toFixed(2)} ${units[unitIndex]}`;
  };

  const getStatusColor = (status?: string) => {
    switch (status) {
      case 'completed':
        return 'default';
      case 'running':
      case 'processing':
        return 'secondary';
      case 'failed':
        return 'destructive';
      default:
        return 'outline';
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  if (error || !archive) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Link href="/archives">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back
            </Button>
          </Link>
        </div>
        <Card>
          <CardContent className="pt-6">
            <p className="text-center text-muted-foreground">Archive not found</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/archives">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back
            </Button>
          </Link>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Archive Details</h1>
            <p className="text-muted-foreground font-mono text-sm">{archiveId}</p>
          </div>
        </div>
        <Badge variant={getStatusColor(archive.status) as any}>
          {archive.status}
        </Badge>
      </div>

      {/* Metadata Card */}
      <Card>
        <CardHeader>
          <CardTitle>Archive Information</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p className="text-sm text-muted-foreground">Created At</p>
              <p className="font-medium">
                {archive.created_at
                  ? format(new Date(archive.created_at), 'MMM d, yyyy HH:mm')
                  : 'N/A'}
              </p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Records</p>
              <p className="font-medium">
                {archive.records_archived?.toLocaleString() || '-'}
              </p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Size</p>
              <p className="font-medium">{formatFileSize(archive.size_bytes)}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">S3 Path</p>
              <p className="font-mono text-xs truncate" title={archive.s3_path}>
                {archive.s3_path || 'N/A'}
              </p>
            </div>
          </div>
          {archive.error_message && (
            <div className="mt-4 p-3 bg-destructive/10 rounded-md">
              <p className="text-sm text-destructive">{archive.error_message}</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Data Viewer Tabs */}
      {archive.status === 'completed' && (
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList>
            <TabsTrigger value="data">Data</TabsTrigger>
            <TabsTrigger value="visualize">Visualize</TabsTrigger>
          </TabsList>

          <TabsContent value="data" className="space-y-4">
            <ArchiveDataViewer archiveId={archiveId} />
          </TabsContent>

          <TabsContent value="visualize" className="space-y-4">
            <ArchiveChart archiveId={archiveId} />
          </TabsContent>
        </Tabs>
      )}
    </div>
  );
}

