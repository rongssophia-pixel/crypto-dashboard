'use client';

/**
 * Email Verification Page
 */

import { Suspense, useEffect, useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api-client';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Loader2, CheckCircle2, XCircle } from 'lucide-react';
import Link from 'next/link';

function VerifyEmailContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('');

  useEffect(() => {
    const token = searchParams.get('token');
    
    if (!token) {
      setStatus('error');
      setMessage('Verification token is missing');
      return;
    }

    const verifyEmail = async () => {
      try {
        await apiClient.post('/api/v1/auth/verify-email', { token });
        setStatus('success');
        setMessage('Email verified successfully!');
        
        // Redirect to dashboard after 3 seconds
        setTimeout(() => {
          router.push('/dashboard');
        }, 3000);
      } catch (error) {
        setStatus('error');
        setMessage(error instanceof Error ? error.message : 'Verification failed');
      }
    };

    verifyEmail();
  }, [searchParams, router]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Email Verification</CardTitle>
        <CardDescription>
          Verifying your email address
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {status === 'loading' && (
          <div className="flex flex-col items-center py-8 space-y-4">
            <Loader2 className="h-12 w-12 animate-spin text-blue-500" />
            <p className="text-slate-600 dark:text-slate-400">
              Verifying your email...
            </p>
          </div>
        )}

        {status === 'success' && (
          <div className="flex flex-col items-center py-8 space-y-4">
            <CheckCircle2 className="h-12 w-12 text-green-500" />
            <Alert>
              <AlertDescription>{message}</AlertDescription>
            </Alert>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Redirecting to dashboard in 3 seconds...
            </p>
          </div>
        )}

        {status === 'error' && (
          <div className="flex flex-col items-center py-8 space-y-4">
            <XCircle className="h-12 w-12 text-red-500" />
            <Alert variant="destructive">
              <AlertDescription>{message}</AlertDescription>
            </Alert>
            <div className="flex gap-2">
              <Button asChild variant="outline">
                <Link href="/login">Go to Login</Link>
              </Button>
              <Button asChild>
                <Link href="/register">Create Account</Link>
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={
      <Card>
        <CardHeader>
          <CardTitle>Email Verification</CardTitle>
          <CardDescription>
            Verifying your email address
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center py-8 space-y-4">
            <Loader2 className="h-12 w-12 animate-spin text-blue-500" />
            <p className="text-slate-600 dark:text-slate-400">
              Loading...
            </p>
          </div>
        </CardContent>
      </Card>
    }>
      <VerifyEmailContent />
    </Suspense>
  );
}






