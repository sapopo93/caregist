import { NextRequest, NextResponse } from 'next/server';

export const config = {
  matcher: [
    /*
     * Match everything EXCEPT:
     *   / (home)
     *   /login, /signup, /privacy, /terms, /cookie-settings
     *   /_next/* (Next.js internals)
     *   /api/* (backend API routes)
     *   common static assets
     */
    '/((?!$|login|signup|privacy|terms|cookie-settings|_next|api).*)',
  ],
};

export function middleware(request: NextRequest) {
  const session = request.cookies.get('caregist_session');

  if (!session?.value) {
    const { pathname, search } = request.nextUrl;
    const next = encodeURIComponent(pathname + search);
    return NextResponse.redirect(
      new URL(`/login?next=${next}`, request.url)
    );
  }

  return NextResponse.next();
}
