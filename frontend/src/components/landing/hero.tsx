'use client';

/**
 * Hero Section
 * Main landing page hero with title, tagline, and CTA buttons
 */

import { Button } from '@/components/ui/button';
import { ArrowRight, BarChart3 } from 'lucide-react';
import Link from 'next/link';
import { useAuth } from '@/hooks/useAuth';
import PixelBlast from './pixel-blast';

export function Hero() {
  const { user } = useAuth();

  return (
    <section className="relative min-h-screen flex flex-col items-center justify-center overflow-hidden bg-[#030303] selection:bg-primary/20">
      {/* Navigation Placeholder */}
      <nav className="absolute top-0 left-0 right-0 z-50 px-6 py-6">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 bg-primary rounded-lg flex items-center justify-center">
              <BarChart3 className="h-5 w-5 text-white" />
            </div>
            <span className="text-lg font-bold text-white tracking-tight">CryptoDash</span>
          </div>
          <div className="hidden md:flex items-center gap-8 text-sm font-medium text-zinc-400">
            <Link href="#features" className="hover:text-white transition-colors">Features</Link>
            <Link href="#pricing" className="hover:text-white transition-colors">Pricing</Link>
            <Link href="#about" className="hover:text-white transition-colors">About</Link>
          </div>
          <div className="flex items-center gap-4">
            <Link href="/login" className="text-sm font-medium text-zinc-400 hover:text-white transition-colors">
              Log in
            </Link>
            <Button asChild size="sm" className="bg-white text-black hover:bg-zinc-200">
              <Link href="/register">Sign up</Link>
            </Button>
          </div>
        </div>
      </nav>

      {/* Animated Background */}
      <PixelBlast
        variant="square"
        pixelSize={6}
        color="#6366f1" 
        patternScale={3}
        patternDensity={1.5}
        pixelSizeJitter={0.2}
        enableRipples
        rippleSpeed={0.5}
        rippleThickness={0.05}
        rippleIntensityScale={2}
        liquid={false}
        speed={0.4}
        edgeFade={0.2}
        transparent
        className="absolute inset-0 z-0 opacity-80"
      />

      {/* Gradient Overlay for Depth */}
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-black/20 to-black z-[5] pointer-events-none" />
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(0,0,0,0)_0%,rgba(3,3,3,1)_100%)] z-[5] pointer-events-none" />

      {/* Content */}
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10 pt-20">
        <div className="max-w-5xl mx-auto text-center space-y-10">
          
          {/* Announcement Pill */}
          <div className="flex justify-center">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 border border-white/10 text-xs font-medium text-zinc-300 hover:bg-white/10 transition-colors cursor-pointer">
              <span className="flex h-2 w-2 rounded-full bg-primary"></span>
              v2.0 is now live
              <ArrowRight className="h-3 w-3 text-zinc-500" />
            </div>
          </div>

          {/* Title */}
          <h1 className="text-5xl sm:text-7xl lg:text-8xl font-semibold tracking-tighter text-white">
            Analytics for the
            <span className="block text-zinc-500">modern trader.</span>
          </h1>

          {/* Description */}
          <p className="text-lg sm:text-xl text-zinc-400 max-w-2xl mx-auto leading-relaxed">
            Professional-grade cryptocurrency market data, real-time analytics, and intelligent alerts. 
            Built for performance, designed for clarity.
          </p>

          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center pt-2">
            {user ? (
              <Button asChild size="lg" className="h-12 px-8 text-base bg-white text-black hover:bg-zinc-200 rounded-full transition-all">
                <Link href="/dashboard">
                  Go to Dashboard
                </Link>
              </Button>
            ) : (
              <>
                <Button asChild size="lg" className="h-12 px-8 text-base bg-white text-black hover:bg-zinc-200 rounded-full transition-all">
                  <Link href="/register">
                    Start Trading
                  </Link>
                </Button>
                <Button asChild size="lg" variant="outline" className="h-12 px-8 text-base bg-transparent border-zinc-800 text-zinc-300 hover:bg-white/5 hover:text-white rounded-full transition-all">
                  <Link href="/login">View Demo</Link>
                </Button>
              </>
            )}
          </div>

          {/* Dashboard Preview / Trust Section */}
          <div className="pt-16 pb-8">
            <p className="text-sm text-zinc-500 font-medium mb-6 uppercase tracking-widest">Trusted by traders at</p>
            <div className="flex flex-wrap justify-center gap-8 opacity-50 grayscale hover:grayscale-0 transition-all duration-500">
               {/* Simple text placeholders for "logos" to keep it clean without needing assets */}
               <span className="text-xl font-bold text-zinc-300">BINANCE</span>
               <span className="text-xl font-bold text-zinc-300">COINBASE</span>
               <span className="text-xl font-bold text-zinc-300">KRAKEN</span>
               <span className="text-xl font-bold text-zinc-300">BYBIT</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
