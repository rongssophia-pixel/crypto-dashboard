'use client';

/**
 * Features Section
 * Showcase key platform capabilities
 */

import { Card, CardContent } from '@/components/ui/card';
import {
  Activity,
  BarChart3,
  Database,
  Bell,
  Globe,
  Shield,
} from 'lucide-react';

const features = [
  {
    icon: Activity,
    title: 'Real-time Streaming',
    description:
      'Live market data via WebSocket connections with sub-second latency. Track price movements as they happen across multiple exchanges.',
  },
  {
    icon: BarChart3,
    title: 'Advanced Analytics',
    description:
      'Interactive OHLCV candlestick charts, technical indicators, and aggregated metrics. Analyze market trends with professional-grade tools.',
  },
  {
    icon: Database,
    title: 'Historical Data',
    description:
      'Query and export years of historical market data. Backtest strategies and analyze long-term trends with our high-performance time-series database.',
  },
  {
    icon: Bell,
    title: 'Smart Alerts',
    description:
      'Set price, volume, and volatility alerts with customizable conditions. Get notified instantly via email or other channels when markets move.',
  },
  {
    icon: Globe,
    title: 'Multi-Exchange',
    description:
      'Connect to major cryptocurrency exchanges including Binance, Coinbase, and more. Unified interface for all your trading data.',
  },
  {
    icon: Shield,
    title: 'Secure & Scalable',
    description:
      'Enterprise-grade microservices architecture with JWT authentication, multi-tenant support, and 99.9% uptime SLA.',
  },
];

export function Features() {
  return (
    <section className="py-24 px-4 sm:px-6 lg:px-8">
      <div className="container mx-auto max-w-7xl">
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto mb-16">
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight mb-4">
            Everything you need to
            <span className="block mt-1 bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">
              trade smarter
            </span>
          </h2>
          <p className="text-lg text-muted-foreground">
            Professional-grade tools and infrastructure for serious cryptocurrency
            traders and analysts
          </p>
        </div>

        {/* Features Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((feature, index) => {
            const Icon = feature.icon;
            return (
              <Card
                key={index}
                className="group hover:shadow-lg transition-all duration-300 hover:-translate-y-1"
              >
                <CardContent className="p-6 space-y-4">
                  <div className="p-3 bg-primary/10 rounded-lg w-fit group-hover:bg-primary/20 transition-colors">
                    <Icon className="h-6 w-6 text-primary" />
                  </div>
                  <h3 className="text-xl font-semibold">{feature.title}</h3>
                  <p className="text-muted-foreground leading-relaxed">
                    {feature.description}
                  </p>
                </CardContent>
              </Card>
            );
          })}
        </div>

        {/* Bottom CTA */}
        <div className="mt-16 text-center">
          <p className="text-sm text-muted-foreground">
            Ready to get started? Create your free account in seconds.
          </p>
        </div>
      </div>
    </section>
  );
}



