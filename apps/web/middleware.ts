import { NextRequest, NextResponse } from "next/server";

const GUARDED_PREFIXES = ["/submit", "/edit", "/review", "/export"];

export function middleware(request: NextRequest) {
  const guarded = GUARDED_PREFIXES.some((prefix) => request.nextUrl.pathname.startsWith(prefix));
  if (!guarded || request.cookies.has("vtn_session")) {
    return undefined;
  }

  return NextResponse.redirect(new URL("/login", request.url));
}

export const config = {
  matcher: ["/submit/:path*", "/edit/:path*", "/review/:path*", "/export/:path*"],
};
