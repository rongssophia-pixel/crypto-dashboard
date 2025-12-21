'use client';

/**
 * Admin Page
 * System administration and management
 */

import { useMemo } from 'react';
import { StreamManagement } from '@/components/admin/stream-management';
import { SystemHealth } from '@/components/admin/system-health';
import { ArchiveManagement } from '@/components/admin/archive-management';
import { Separator } from '@/components/ui/separator';
import { useStreams, useStartStream, useStopStream } from '@/hooks/api/useStreams';
import { useArchives, useCreateArchive, useDownloadArchive } from '@/hooks/api/useArchives';
import { toast } from 'sonner';

export default function AdminPage() {
  // Fetch streams data
  const { data: streamsResponse, isLoading: streamsLoading } = useStreams();
  const startStreamMutation = useStartStream();
  const stopStreamMutation = useStopStream();

  // Fetch archives data
  const { data: archives, isLoading: archivesLoading } = useArchives(20);
  const createArchiveMutation = useCreateArchive();
  const downloadArchiveMutation = useDownloadArchive();

  // Transform streams data
  const streams = useMemo(() => {
    const streamsList = streamsResponse?.streams || [];
    return streamsList.map((stream: any) => ({
      id: stream.stream_id || stream.id,
      symbols: stream.symbols || [],
      status: stream.is_active ? ('running' as const) : ('stopped' as const),
      event_count: stream.events_processed || stream.event_count || 0,
      started_at: stream.started_at || stream.created_at,
    }));
  }, [streamsResponse]);

  // Handle start stream
  const handleStartStream = async (symbols: string[]) => {
    try {
      await startStreamMutation.mutateAsync({
        symbols,
        stream_type: 'ticker',
      });
      toast.success('Stream started successfully');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to start stream');
      throw error; // Re-throw so component can handle it
    }
  };

  // Handle stop stream
  const handleStopStream = async (id: string) => {
    try {
      await stopStreamMutation.mutateAsync(id);
      toast.success('Stream stopped successfully');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to stop stream');
      throw error;
    }
  };

  // Handle create archive
  const handleCreateArchive = async () => {
    try {
      // Create archive for last 24 hours of all data
      const endTime = new Date();
      const startTime = new Date(endTime.getTime() - 24 * 60 * 60 * 1000);
      
      await createArchiveMutation.mutateAsync({
        start_time: startTime.toISOString(),
        end_time: endTime.toISOString(),
        data_type: 'market_data',
      });
      toast.success('Archive creation started');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to create archive');
      throw error;
    }
  };

  // Handle download archive
  const handleDownload = async (id: string) => {
    try {
      const s3Path = await downloadArchiveMutation.mutateAsync(id);
      
      // For now, just show the S3 path. In production, you'd want a signed URL
      toast.success(`Archive available at: ${s3Path}`);
      
      // If you have a download URL, you could trigger a download:
      // const link = document.createElement('a');
      // link.href = downloadUrl;
      // link.download = `archive-${id}.parquet`;
      // link.click();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to download archive');
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Admin Panel</h1>
        <p className="text-muted-foreground">
          System administration and stream management
        </p>
      </div>

      {/* Stream Management */}
      <StreamManagement
        streams={streams}
        isLoading={streamsLoading}
        onStartStream={handleStartStream}
        onStopStream={handleStopStream}
      />

      <Separator />

      {/* System Health */}
      <SystemHealth />

      <Separator />

      {/* Archive Management */}
      <ArchiveManagement
        archives={archives || []}
        isLoading={archivesLoading}
        onCreateArchive={handleCreateArchive}
        onDownload={handleDownload}
      />
    </div>
  );
}
