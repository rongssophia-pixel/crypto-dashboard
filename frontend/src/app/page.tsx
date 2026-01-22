'use client';

/**
 * Landing Page
 * Public homepage with hero section and features
 */

import { Hero } from '@/components/landing/hero';
import { Features } from '@/components/landing/features';

export default function HomePage() {
  return (
    <main className="min-h-screen">
      <Hero />
      <Features />
    </main>
  );
}
