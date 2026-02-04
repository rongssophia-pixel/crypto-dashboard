'use client';

import { cn } from '@/lib/utils';

interface RollingNumberProps {
  value: number;
  prefix?: string;
  suffix?: string;
  decimals?: number;
  className?: string;
}

function Digit({ char }: { char: string }) {
  const isNumber = /^[0-9]$/.test(char);

  if (!isNumber) {
    return <span>{char}</span>;
  }

  const n = parseInt(char, 10);

  return (
    <span className="inline-block overflow-hidden h-[1em] align-top relative" style={{ lineHeight: '1em' }}>
      <span
        className="flex flex-col transition-transform duration-500 ease-[cubic-bezier(0.23,1,0.32,1)]"
        style={{ transform: `translateY(-${n * 10}%)` }}
      >
        {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9].map((i) => (
          <span key={i} className="h-[1em] flex items-center justify-center">
            {i}
          </span>
        ))}
      </span>
    </span>
  );
}

export function RollingNumber({
  value,
  prefix = '',
  suffix = '',
  decimals = 2,
  className,
}: RollingNumberProps) {
  // Use toLocaleString to get formatted number with commas (e.g. "1,234.56")
  // Using fixed decimals to prevent jumping layout
  const formatted = value.toLocaleString(undefined, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });

  const fullText = `${prefix}${formatted}${suffix}`;
  const chars = fullText.split('');

  return (
    <div className={cn("inline-flex items-baseline overflow-hidden", className)}>
      {chars.map((char, index) => (
        // Use index as key so digits in the same position animate
        <Digit key={index} char={char} />
      ))}
    </div>
  );
}
