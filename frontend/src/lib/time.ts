/**
 * Time Zone Utilities
 * Handles conversion between UTC and user's local timezone
 */

import { format, formatDistanceToNow, parseISO } from 'date-fns';
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
