import { auth, isDevBypassEnabled } from '@/lib/auth';
import { NextResponse } from 'next/server';

export default auth((req) => {
  const isAdminPath = req.nextUrl.pathname.startsWith('/admin') && req.nextUrl.pathname !== '/admin/login';
  if (isAdminPath && !req.auth && !isDevBypassEnabled()) {
    return NextResponse.redirect(new URL('/admin/login', req.url));
  }
  return NextResponse.next();
});

export const config = { matcher: ['/admin/:path*', '/api/admin/:path*'] };
