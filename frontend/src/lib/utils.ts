import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Format number with full precision, removing trailing zeros
 * @param value - The number to format
 * @param maxDecimals - Maximum decimal places (optional, for very long decimals)
 * @returns Formatted string with trailing zeros removed
 */
export function formatNumber(value: number, maxDecimals?: number): string {
  if (isNaN(value) || !isFinite(value)) {
    return '0';
  }
  
  // Convert to string, removing trailing zeros
  let str = maxDecimals !== undefined 
    ? value.toFixed(maxDecimals)
    : value.toString();
  
  // Remove trailing zeros after decimal point
  if (str.includes('.')) {
    str = str.replace(/\.?0+$/, '');
  }
  
  return str;
}

/**
 * Format price with dollar sign, full precision, removing trailing zeros
 */
export function formatPrice(value: number, maxDecimals?: number): string {
  return `$${formatNumber(value, maxDecimals)}`;
}

/**
 * Format percentage with full precision, removing trailing zeros
 */
export function formatPercentage(value: number, maxDecimals?: number): string {
  return `${formatNumber(value, maxDecimals)}%`;
}
