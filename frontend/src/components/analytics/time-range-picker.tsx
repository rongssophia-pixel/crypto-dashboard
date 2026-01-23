'use client';

/**
 * Time Range Picker Component
 * Preset time ranges for data queries
 */

import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { cn } from '@/lib/utils';

export interface TimeRange {
  label: string;
  value: string;
  hours: number;
}

const TIME_RANGES: TimeRange[] = [
  { label: '1H', value: '1h', hours: 1 },
  { label: '4H', value: '4h', hours: 4 },
  { label: '24H', value: '24h', hours: 24 },
  { label: '7D', value: '7d', hours: 168 },
  { label: '30D', value: '30d', hours: 720 },
];

interface TimeRangePickerProps {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}

export function TimeRangePicker({ value, onChange, disabled }: TimeRangePickerProps) {
  return (
    <div className="space-y-2">
      <Label>Time Range</Label>
      <div className="flex flex-wrap gap-2">
        {TIME_RANGES.map((range) => (
          <Button
            key={range.value}
            variant={value === range.value ? 'default' : 'outline'}
            size="sm"
            onClick={() => onChange(range.value)}
            disabled={disabled}
            className={cn(
              'min-w-[60px]',
              value === range.value && 'bg-blue-600 hover:bg-blue-700'
            )}
          >
            {range.label}
          </Button>
        ))}
      </div>
    </div>
  );
}

// Helper to get time range in hours
export function getTimeRangeHours(value: string): number {
  const range = TIME_RANGES.find((r) => r.value === value);
  return range?.hours || 24;
}

// Helper to calculate start and end times
export function getTimeRangeDates(value: string): { start_time: string; end_time: string } {
  const hours = getTimeRangeHours(value);
  const end = new Date();
  const start = new Date(end.getTime() - hours * 60 * 60 * 1000);
  return { 
    start_time: start.toISOString(), 
    end_time: end.toISOString() 
  };
}


