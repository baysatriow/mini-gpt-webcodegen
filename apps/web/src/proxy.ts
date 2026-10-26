import { NextResponse, type NextRequest } from "next/server";
import {
  isAccessConfigured,
  isAccessRequired,
  SESSION_COOKIE_NAME,
  verifySessionToken,
} from "@/lib/access-session.mjs";

function isAuthRoute(pathname: string) {
  return pathname === "/login" || pathname === "/api/auth/login" || pathname === "/api/auth/logout";
}

function unavailable(request: NextRequest) {
  if (request.nextUrl.pathname.startsWith("/api/")) {
    return NextResponse.json({ error: "access_configuration_unavailable" }, { status: 503 });
  }
  return NextResponse.redirect(new URL("/login?unavailable=1", request.url));
}

export function proxy(request: NextRequest) {
  const pathname = request.nextUrl.pathname;
  if (!isAccessRequired()) {
    if (pathname === "/login") return NextResponse.redirect(new URL("/", request.url));
    return NextResponse.next();
  }

  if (!isAccessConfigured()) {
    if (isAuthRoute(pathname)) return NextResponse.next();
    return unavailable(request);
  }

  const secret = process.env.APP_SESSION_SECRET!;
  const validSession = verifySessionToken(
    request.cookies.get(SESSION_COOKIE_NAME)?.value,
    secret,
  );

  if (pathname === "/login") {
    return validSession ? NextResponse.redirect(new URL("/", request.url)) : NextResponse.next();
  }
  if (pathname === "/api/auth/login" || pathname === "/api/auth/logout") {
    return NextResponse.next();
  }
  if (validSession) return NextResponse.next();

  if (pathname.startsWith("/api/")) {
    return NextResponse.json({ error: "authentication_required" }, { status: 401 });
  }
  return NextResponse.redirect(new URL("/login", request.url));
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
