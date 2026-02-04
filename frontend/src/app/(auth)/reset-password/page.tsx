'use client';

/**
 * Reset Password Page
 */

import { Suspense, useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api-client';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, CheckCircle2, XCircle } from 'lucide-react';
import Link from 'next/link';

function ResetPasswordContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const token = searchParams.get('token');

  // Password strength validation
  const passwordRequirements = [
    { label: 'At least 8 characters', test: (p: string) => p.length >= 8 },
    { label: 'Contains uppercase letter', test: (p: string) => /[A-Z]/.test(p) },
    { label: 'Contains lowercase letter', test: (p: string) => /[a-z]/.test(p) },
    { label: 'Contains number', test: (p: string) => /[0-9]/.test(p) },
    { label: 'Contains special character', test: (p: string) => /[^A-Za-z0-9]/.test(p) },
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!token) {
      setError('Reset token is missing');
      return;
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    const allRequirementsMet = passwordRequirements.every((req) => req.test(password));
    if (!allRequirementsMet) {
      setError('Password does not meet all requirements');
      return;
    }

    setIsLoading(true);

    try {
      await apiClient.post('/api/v1/auth/reset-password', {
        token,
        new_password: password,
      });
      setSuccess(true);
      
      // Redirect to login after 3 seconds
      setTimeout(() => {
        router.push('/login');
      }, 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Password reset failed');
    } finally {
      setIsLoading(false);
    }
  };

  if (!token) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Invalid Link</CardTitle>
          <CardDescription>Password reset token is missing</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Alert variant="destructive">
            <AlertDescription>
              This password reset link is invalid or has expired.
            </AlertDescription>
          </Alert>
        </CardContent>
        <CardFooter>
          <Button asChild className="w-full">
            <Link href="/forgot-password">Request New Link</Link>
          </Button>
        </CardFooter>
      </Card>
    );
  }

  if (success) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Password Reset Successful</CardTitle>
          <CardDescription>Your password has been updated</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col items-center py-8 space-y-4">
            <CheckCircle2 className="h-12 w-12 text-green-500" />
            <Alert>
              <AlertDescription>
                Your password has been successfully reset. You can now log in with your new password.
              </AlertDescription>
            </Alert>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Redirecting to login in 3 seconds...
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Set New Password</CardTitle>
        <CardDescription>
          Enter your new password
        </CardDescription>
      </CardHeader>
      <form onSubmit={handleSubmit}>
        <CardContent className="space-y-4">
          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
          
          <div className="space-y-2">
            <Label htmlFor="password">New Password</Label>
            <Input
              id="password"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              disabled={isLoading}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="confirmPassword">Confirm Password</Label>
            <Input
              id="confirmPassword"
              type="password"
              placeholder="••••••••"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              disabled={isLoading}
            />
          </div>

          {password && (
            <div className="space-y-2 p-3 bg-slate-50 dark:bg-slate-900 rounded-md">
              <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
                Password Requirements:
              </p>
              <ul className="space-y-1">
                {passwordRequirements.map((req) => {
                  const met = req.test(password);
                  return (
                    <li
                      key={req.label}
                      className="flex items-center text-sm"
                    >
                      {met ? (
                        <CheckCircle2 className="h-4 w-4 text-green-500 mr-2" />
                      ) : (
                        <XCircle className="h-4 w-4 text-slate-400 mr-2" />
                      )}
                      <span className={met ? 'text-green-700 dark:text-green-400' : 'text-slate-600 dark:text-slate-400'}>
                        {req.label}
                      </span>
                    </li>
                  );
                })}
              </ul>
            </div>
          )}
        </CardContent>

        <CardFooter>
          <Button type="submit" className="w-full" disabled={isLoading}>
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Resetting password...
              </>
            ) : (
              'Reset Password'
            )}
          </Button>
        </CardFooter>
      </form>
    </Card>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={
      <Card>
        <CardHeader>
          <CardTitle>Reset Password</CardTitle>
          <CardDescription>Loading...</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
          </div>
        </CardContent>
      </Card>
    }>
      <ResetPasswordContent />
    </Suspense>
  );
}






