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

interface SymbolSelectorProps {
  value: string;
  onChange: (value: string) => void;
  symbols: string[];
  disabled?: boolean;
}

export function SymbolSelector({ value, onChange, symbols, disabled }: SymbolSelectorProps) {
  return (
    <div className="space-y-2">
      <Label>Symbol</Label>
      <Select value={value} onValueChange={onChange} disabled={disabled || symbols.length === 0}>
        <SelectTrigger className="w-full md:w-48">
          <SelectValue placeholder={symbols.length === 0 ? "No symbols in watchlist" : "Select symbol"} />
        </SelectTrigger>
        <SelectContent>
          {symbols.map((symbol) => (
            <SelectItem key={symbol} value={symbol}>
              {symbol}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

