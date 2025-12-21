'use client';

/**
 * Symbol Selector Component
 * Dropdown to select cryptocurrency symbols
 */

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Label } from '@/components/ui/label';

const POPULAR_SYMBOLS = [
  'BTCUSDT',
  'ETHUSDT',
  'BNBUSDT',
  'ADAUSDT',
  'DOGEUSDT',
  'XRPUSDT',
  'DOTUSDT',
  'UNIUSDT',
  'LINKUSDT',
  'SOLUSDT',
];

interface SymbolSelectorProps {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}

export function SymbolSelector({ value, onChange, disabled }: SymbolSelectorProps) {
  return (
    <div className="space-y-2">
      <Label>Symbol</Label>
      <Select value={value} onValueChange={onChange} disabled={disabled}>
        <SelectTrigger className="w-full md:w-48">
          <SelectValue placeholder="Select symbol" />
        </SelectTrigger>
        <SelectContent>
          {POPULAR_SYMBOLS.map((symbol) => (
            <SelectItem key={symbol} value={symbol}>
              {symbol}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
