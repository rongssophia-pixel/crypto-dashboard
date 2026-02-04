/**
 * Auth Layout
 * Centered card layout for authentication pages
 */

import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Authentication | Crypto Analytics',
};

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-100">
            Crypto Analytics
          </h1>
          <p className="text-slate-600 dark:text-slate-400 mt-2">
            Real-time cryptocurrency market data platform
          </p>
        </div>
        {children}
      </div>
    </div>
  );
}






