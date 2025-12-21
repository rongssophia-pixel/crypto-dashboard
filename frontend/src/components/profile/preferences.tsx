'use client';

/**
 * Preferences Component
 * User preferences and settings
 */

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Button } from '@/components/ui/button';
import { useTheme } from 'next-themes';
import { getUserTimeZone, setUserTimeZone } from '@/lib/time';
import { useState, useEffect } from 'react';
import { toast } from 'sonner';

const TIMEZONES = [
  { label: 'UTC', value: 'UTC' },
  { label: 'America/New_York (EST)', value: 'America/New_York' },
  { label: 'America/Chicago (CST)', value: 'America/Chicago' },
  { label: 'America/Los_Angeles (PST)', value: 'America/Los_Angeles' },
  { label: 'Europe/London (GMT)', value: 'Europe/London' },
  { label: 'Europe/Paris (CET)', value: 'Europe/Paris' },
  { label: 'Asia/Tokyo (JST)', value: 'Asia/Tokyo' },
  { label: 'Asia/Shanghai (CST)', value: 'Asia/Shanghai' },
  { label: 'Australia/Sydney (AEDT)', value: 'Australia/Sydney' },
];

export function Preferences() {
  const { theme, setTheme } = useTheme();
  const [timezone, setTimezone] = useState<string>(getUserTimeZone());
  const [emailNotifications, setEmailNotifications] = useState(true);
  const [priceAlerts, setPriceAlerts] = useState(true);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    // Load saved preferences from localStorage
    const savedEmailNotif = localStorage.getItem('email_notifications');
    const savedPriceAlerts = localStorage.getItem('price_alerts');
    
    if (savedEmailNotif !== null) {
      setEmailNotifications(savedEmailNotif === 'true');
    }
    if (savedPriceAlerts !== null) {
      setPriceAlerts(savedPriceAlerts === 'true');
    }
  }, []);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      // Save preferences
      setUserTimeZone(timezone);
      localStorage.setItem('email_notifications', emailNotifications.toString());
      localStorage.setItem('price_alerts', priceAlerts.toString());
      
      // In a real app, this would make an API call to save preferences
      await new Promise((resolve) => setTimeout(resolve, 500));
      
      toast.success('Preferences saved successfully');
    } catch (error) {
      toast.error('Failed to save preferences');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Preferences</CardTitle>
        <CardDescription>Customize your experience</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Theme */}
        <div className="space-y-2">
          <Label htmlFor="theme">Theme</Label>
          <Select value={theme} onValueChange={setTheme}>
            <SelectTrigger id="theme">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="light">Light</SelectItem>
              <SelectItem value="dark">Dark</SelectItem>
              <SelectItem value="system">System</SelectItem>
            </SelectContent>
          </Select>
          <p className="text-xs text-muted-foreground">
            Choose your preferred color scheme
          </p>
        </div>

        {/* Timezone */}
        <div className="space-y-2">
          <Label htmlFor="timezone">Timezone</Label>
          <Select value={timezone} onValueChange={setTimezone}>
            <SelectTrigger id="timezone">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {TIMEZONES.map((tz) => (
                <SelectItem key={tz.value} value={tz.value}>
                  {tz.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <p className="text-xs text-muted-foreground">
            All times will be displayed in this timezone
          </p>
        </div>

        {/* Email Notifications */}
        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <Label htmlFor="email-notifications">Email Notifications</Label>
            <p className="text-xs text-muted-foreground">
              Receive updates via email
            </p>
          </div>
          <Switch
            id="email-notifications"
            checked={emailNotifications}
            onCheckedChange={setEmailNotifications}
          />
        </div>

        {/* Price Alerts */}
        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <Label htmlFor="price-alerts">Price Alerts</Label>
            <p className="text-xs text-muted-foreground">
              Get notified about price changes
            </p>
          </div>
          <Switch
            id="price-alerts"
            checked={priceAlerts}
            onCheckedChange={setPriceAlerts}
          />
        </div>

        {/* Save Button */}
        <div className="pt-4">
          <Button onClick={handleSave} disabled={isSaving} className="w-full">
            {isSaving ? 'Saving...' : 'Save Preferences'}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
