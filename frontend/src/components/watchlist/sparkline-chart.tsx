'use client';

/**
 * Sparkline Chart Component
 * Simplified line chart for watchlist cards
 */

import { ResponsiveContainer, LineChart, Line, YAxis } from 'recharts';

interface SparklineData {
  timestamp: string;
  value: number;
}

interface SparklineChartProps {
  data: SparklineData[];
  color?: string;
  height?: number;
}

export function SparklineChart({ data, color = '#22c55e', height = 60 }: SparklineChartProps) {
  if (!data || data.length === 0) return null;

  // Calculate min/max for domain to make the chart look better
  const values = data.map(d => d.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const buffer = (max - min) * 0.1;

  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <YAxis 
            domain={[min - buffer, max + buffer]} 
            hide 
          />
          <Line
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

