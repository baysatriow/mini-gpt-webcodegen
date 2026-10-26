import { isAccessRequired, isSameHostOrigin, SESSION_COOKIE_NAME } from "@/lib/access-session.mjs";

export async function POST(request: Request) {
  const forwardedProtocol = request.headers.get("x-forwarded-proto")?.split(",")[0]?.trim().toLowerCase();
  const secure = new URL(request.url).protocol === "https:" || forwardedProtocol === "https";
  const headers = new Headers({ "Cache-Control": "no-store" });
  if (!isAccessRequired()) {
    return Response.json({ error: "not_found" }, { status: 404, headers });
  }
  if (!isSameHostOrigin(request.headers.get("origin") ?? undefined, request.headers.get("host") ?? undefined)) {
    return Response.json({ error: "invalid_request_origin" }, { status: 403, headers });
  }
  const cookie = [
    `${SESSION_COOKIE_NAME}=`,
    "Path=/",
    "Max-Age=0",
    "HttpOnly",
    "SameSite=Lax",
    ...(secure ? ["Secure"] : []),
  ].join("; ");
  headers.set("Set-Cookie", cookie);
  headers.set("Location", "/login");
  return new Response(null, { status: 303, headers });
}
