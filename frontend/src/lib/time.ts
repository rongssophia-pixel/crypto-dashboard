/**
 * Time Zone Utilities
 * Handles conversion between UTC and user's local timezone
 */

import { formatDistanceToNow, parseISO, subDays, subHours, subMonths, subYears, startOfDay, startOfYear } from 'date-fns';
import { formatInTimeZone } from 'date-fns-tz';

/**
 * Get user's timezone from browser or preference
 */
export function getUserTimeZone(): string {
  // Check for user preference in localStorage
  if (typeof window !== 'undefined') {
    const savedTz = localStorage.getItem('user_timezone');
    if (savedTz) return savedTz;
  }

  // Fall back to browser's detected timezone
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone;
  } catch (error) {
    console.error('Failed to get timezone:', error);
    return 'UTC';
  }
}

/**
 * Set user's timezone preference
 */
export function setUserTimeZone(timezone: string): void {
  if (typeof window !== 'undefined') {
    localStorage.setItem('user_timezone', timezone);
  }
}

/**
 * Format UTC ISO string to user's timezone
 * @param isoString - UTC ISO 8601 string from API
 * @param formatStr - date-fns format string (default: 'PPpp')
 */
export function formatInUserTimeZone(
  isoString: string,
  formatStr: string = 'PPpp'
): string {
  try {
    const userTz = getUserTimeZone();
    const date = parseISO(isoString);
    return formatInTimeZone(date, userTz, formatStr);
  } catch (error) {
    console.error('Failed to format date:', error);
    return isoString;
  }
}

/**
 * Format as relative time (e.g., "2 hours ago")
 */
export function formatRelative(isoString: string): string {
  try {
    const date = parseISO(isoString);
    return formatDistanceToNow(date, { addSuffix: true });
  } catch (error) {
    console.error('Failed to format relative date:', error);
    return isoString;
  }
}

/**
 * Format for display in tables/charts
 * @param isoString - UTC ISO 8601 string
 * @param formatStr - Optional format string
 */
export function formatDateTime(
  isoString: string,
  formatStr: string = 'MMM dd, yyyy HH:mm:ss'
): string {
  return formatInUserTimeZone(isoString, formatStr);
}

/**
 * Get current time in UTC ISO format (for API requests)
 */
export function getCurrentUTCIso(): string {
  return new Date().toISOString();
}

/**
 * Convert local date to UTC ISO for API
 */
export function toUTCIso(date: Date): string {
  return date.toISOString();
}

/**
 * Time range presets
 */
export type TimeRangePreset = '1D' | '5D' | '1M' | '6M' | 'YTD' | '1Y' | '5Y' | 'MAX';

/**
 * Get start/end time for a preset range
 */
export function getTimeRangeFromPreset(preset: TimeRangePreset): { start: Date; end: Date } {
  const end = new Date();
  let start = new Date();

  switch (preset) {
    case '1D':
      start = subDays(end, 1);
      break;
    case '5D':
      start = subDays(end, 5);
      break;
    case '1M':
      start = subMonths(end, 1);
      break;
    case '6M':
      start = subMonths(end, 6);
      break;
    case 'YTD':
      start = startOfYear(end);
      break;
    case '1Y':
      start = subYears(end, 1);
      break;
    case '5Y':
      start = subYears(end, 5);
      break;
    case 'MAX':
      start = subYears(end, 10); // Approximation for "all time"
      break;
    default:
      start = subDays(end, 1);
  }

  return { start, end };
}

/**
 * Get appropriate candle interval for a time range
 */
export function getIntervalForTimeRange(preset: TimeRangePreset): string {
  switch (preset) {
    case '1D':
      return '5m';
    case '5D':
      return '30m';
    case '1M':
      return '4h';
    case '6M':
    case 'YTD':
      return '1d';
    case '1Y':
    case '5Y':
    case 'MAX':
      return '1d'; // Could use 1w if supported, but 1d is granular enough
    default:
      return '1h';
  }
}



