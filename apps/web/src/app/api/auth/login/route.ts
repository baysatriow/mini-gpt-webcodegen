import {
  constantTimeStringEqual,
  createSessionToken,
  isAccessConfigured,
  isAccessRequired,
  SESSION_COOKIE_NAME,
  SESSION_MAX_AGE_SECONDS,
  isSameHostOrigin,
} from "@/lib/access-session.mjs";
import {
  readJsonWithByteLimit,
  RequestBodyTooLargeError,
} from "@/lib/read-limited-json.mjs";

const noStore = { "Cache-Control": "no-store" };
const MAX_LOGIN_BODY_BYTES = 4096;

export async function POST(request: Request) {
  if (!isAccessRequired()) {
    return Response.json({ error: "not_found" }, { status: 404, headers: noStore });
  }
  if (!isAccessConfigured()) {
    return Response.json({ error: "access_configuration_unavailable" }, { status: 503, headers: noStore });
  }
  if (!isSameHostOrigin(request.headers.get("origin") ?? undefined, request.headers.get("host") ?? undefined)) {
    return Response.json({ error: "invalid_request_origin" }, { status: 403, headers: noStore });
  }

  let body: unknown;
  try {
    body = await readJsonWithByteLimit(request, MAX_LOGIN_BODY_BYTES);
  } catch (error) {
    const status = error instanceof RequestBodyTooLargeError ? 413 : 400;
    return Response.json({ error: "invalid_request" }, { status, headers: noStore });
  }
  if (
    !body ||
    typeof body !== "object" ||
    typeof (body as { username?: unknown }).username !== "string" ||
    typeof (body as { password?: unknown }).password !== "string"
  ) {
    return Response.json({ error: "invalid_credentials" }, { status: 401, headers: noStore });
  }

  const { username, password } = body as { username: string; password: string };
  if (
    !constantTimeStringEqual(username, process.env.APP_ACCESS_USERNAME!) ||
    !constantTimeStringEqual(password, process.env.APP_ACCESS_PASSWORD!)
  ) {
    return Response.json({ error: "invalid_credentials" }, { status: 401, headers: noStore });
  }

  const token = createSessionToken(process.env.APP_SESSION_SECRET!);
  const forwardedProtocol = request.headers.get("x-forwarded-proto")?.split(",")[0]?.trim().toLowerCase();
  const secure = new URL(request.url).protocol === "https:" || forwardedProtocol === "https";
  const cookie = [
    `${SESSION_COOKIE_NAME}=${token}`,
    "Path=/",
    `Max-Age=${SESSION_MAX_AGE_SECONDS}`,
    "HttpOnly",
    "SameSite=Lax",
    ...(secure ? ["Secure"] : []),
  ].join("; ");
  return Response.json(
    { ok: true },
    { status: 200, headers: { ...noStore, "Set-Cookie": cookie } },
  );
}
