import type { NextRequest } from "next/server";

type RouteContext = { params: Promise<{ path: string[] }> };

function upstreamUrl(request: NextRequest, path: string[]) {
  const configured = process.env.DJANGO_API_BASE_URL;
  if (!configured) throw new Error("Backend is unavailable");
  const base = new URL(configured.endsWith("/") ? configured : `${configured}/`);
  if (base.protocol !== "http:" && base.protocol !== "https:") {
    throw new Error("Backend is unavailable");
  }
  const encodedPath = path.map(encodeURIComponent).join("/");
  const upstream = new URL(encodedPath, base);
  upstream.search = request.nextUrl.search;
  return upstream;
}

function sanitizedText(value: string) {
  const configured = process.env.DJANGO_API_BASE_URL;
  if (!configured) return value;
  const base = new URL(configured.endsWith("/") ? configured.slice(0, -1) : configured);
  const basePath = base.pathname.replace(/\/$/, "");
  let result = value;
  for (const protocol of ["http:", "https:"]) {
    result = result.replaceAll(`${protocol}//${base.host}${basePath}`, "/backend-api");
    result = result.replaceAll(`${protocol}//${base.host}`, "");
  }
  return result;
}

async function proxy(request: NextRequest, context: RouteContext) {
  try {
    const { path } = await context.params;
    const headers = new Headers({ "X-Forwarded-Proto": "https" });
    const forwardedFor = request.headers.get("x-forwarded-for");
    const realIp = request.headers.get("x-real-ip");
    if (forwardedFor) headers.set("X-Forwarded-For", forwardedFor);
    if (realIp) headers.set("X-Real-IP", realIp);
    const contentType = request.headers.get("content-type");
    if (contentType) headers.set("Content-Type", contentType);

    const upstream = await fetch(upstreamUrl(request, path), {
      method: request.method,
      headers,
      body: request.method === "POST" ? await request.arrayBuffer() : undefined,
      credentials: "omit",
      cache: "no-store",
      redirect: "manual",
    });
    const responseHeaders = new Headers();
    const upstreamContentType = upstream.headers.get("content-type");
    if (upstreamContentType) responseHeaders.set("Content-Type", upstreamContentType);
    const isText = upstreamContentType?.includes("json") || upstreamContentType?.startsWith("text/");
    const body = upstream.status === 204 || upstream.status === 304
      ? null
      : isText
        ? sanitizedText(await upstream.text())
        : upstream.body;
    return new Response(body, {
      status: upstream.status,
      headers: responseHeaders,
    });
  } catch {
    return Response.json({ detail: "Backend service unavailable." }, { status: 502 });
  }
}

export const GET = proxy;
export const POST = proxy;
