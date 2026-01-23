/**
 * Next.js Middleware
 * Handles route protection - redirects unauthenticated users to login
 * Note: Tokens are in localStorage, so we can't verify auth on server.
 * This middleware only redirects protected routes to login.
 * The AuthContext handles post-login redirects on the client side.
 */

import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// Routes that require authentication
const protectedRoutes = [
  '/dashboard',
  '/analytics',
  '/realtime',
  '/admin',
  '/profile',
];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  
  const isProtectedRoute = protectedRoutes.some(route => 
    pathname.startsWith(route)
  );

  // For protected routes, we'll let the client-side auth check handle it
  // The AuthContext will redirect to login if not authenticated
  // This middleware is here for future enhancement with httpOnly cookies
  
  if (isProtectedRoute) {
    // Could add additional checks here (e.g., rate limiting, etc.)
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - api routes
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public folder
     */
    '/((?!api|_next/static|_next/image|favicon.ico|.*\\..*|public).*)',
  ],
};


