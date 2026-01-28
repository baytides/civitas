import { NextRequest, NextResponse } from "next/server";

/**
 * Proxy to add trailing slashes to page routes only.
 * API routes (/api/*) are excluded so they pass through cleanly to FastAPI
 * without redirect loops (FastAPI strips trailing slashes, Next.js adds them).
 */
export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Skip API routes — let rewrites handle them directly
  if (pathname.startsWith("/api/")) {
    return NextResponse.next();
  }

  // Skip static files and Next.js internals
  if (
    pathname.startsWith("/_next/") ||
    pathname.includes(".") // files with extensions (e.g. .css, .js, .ico)
  ) {
    return NextResponse.next();
  }

  // Add trailing slash to page routes (matching trailingSlash: true behavior)
  if (!pathname.endsWith("/")) {
    const url = request.nextUrl.clone();
    url.pathname = `${pathname}/`;
    return NextResponse.redirect(url, 308);
  }

  return NextResponse.next();
}

export const config = {
  // Run on all routes except static assets
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
