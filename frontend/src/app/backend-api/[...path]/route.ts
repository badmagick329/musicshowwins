import type { NextRequest } from "next/server";
import { getServerApiBaseUrl } from "@/lib/api-server";
import { ArchiveRequestError, readArchive } from "@/lib/archive-read";
import { ApiRequestError } from "@/lib/api-shared";
import { checkProxyRateLimit } from "@/lib/proxy-rate-limit";

type RouteContext = { params: Promise<{ path: string[] }> };
// Covers all 2,300 permitted characters even as twelve-byte surrogate escapes.
const MAX_CORRECTION_BODY_BYTES = 32_768;

class BodyTooLarge extends Error {}

async function correctionBody(request: NextRequest) {
  const declaredLength = request.headers.get("content-length");
  if (declaredLength && /^\d+$/.test(declaredLength) && Number(declaredLength) > MAX_CORRECTION_BODY_BYTES) {
    void request.body?.cancel().catch(() => {});
    throw new BodyTooLarge();
  }
  if (!request.body) return new ArrayBuffer(0);

  const reader = request.body.getReader();
  const bytes = new Uint8Array(MAX_CORRECTION_BODY_BYTES);
  let size = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) return bytes.buffer.slice(0, size);
      if (value.byteLength > MAX_CORRECTION_BODY_BYTES - size) {
        void reader.cancel().catch(() => {});
        throw new BodyTooLarge();
      }
      bytes.set(value, size);
      size += value.byteLength;
    }
  } finally {
    reader.releaseLock();
  }
}

function upstreamUrl(request: NextRequest, path: string[]) {
  if (path.some((segment) => segment === "" || segment === "." || segment === "..")) return null;
  const configured = getServerApiBaseUrl();
  const base = new URL(configured.endsWith("/") ? configured : `${configured}/`);
  if (base.protocol !== "http:" && base.protocol !== "https:") {
    throw new Error("Backend is unavailable");
  }
  const encodedPath = path.map(encodeURIComponent).join("/");
  const upstream = new URL(encodedPath, base);
  const basePath = base.pathname.endsWith("/") ? base.pathname : `${base.pathname}/`;
  if (!upstream.pathname.startsWith(basePath)) return null;
  upstream.search = request.nextUrl.search;
  return upstream;
}

function sanitizedText(value: string) {
  const configured = getServerApiBaseUrl();
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
    if (request.method === "POST" && (path.length !== 1 || path[0] !== "corrections")) {
      return Response.json({ detail: "Not found." }, { status: 404 });
    }
    const target = upstreamUrl(request, path);
    if (!target) return Response.json({ detail: "Not found." }, { status: 404 });
    if (request.method === "GET") {
      const forwardedFor = request.headers.get("x-forwarded-for");
      const realIp = request.headers.get("x-real-ip");
      const clientIp = forwardedFor?.split(",").at(-1)?.trim() || realIp?.trim() || "shared";
      const limit = checkProxyRateLimit(clientIp);
      if (!limit.allowed) {
        return Response.json({ detail: "Too many requests." }, {
          status: 429,
          headers: { "Retry-After": String(limit.retryAfter) },
        });
      }
      const upstream = await readArchive(target.toString(), request.signal);
      return new Response(sanitizedText(JSON.stringify(upstream.data)), {
        status: upstream.status,
        headers: { "Content-Type": upstream.contentType || "application/json" },
      });
    }
    const headers = new Headers({ "X-Forwarded-Proto": "https" });
    const forwardedFor = request.headers.get("x-forwarded-for");
    const realIp = request.headers.get("x-real-ip");
    if (forwardedFor) headers.set("X-Forwarded-For", forwardedFor);
    if (realIp) headers.set("X-Real-IP", realIp);
    const contentType = request.headers.get("content-type");
    if (contentType) headers.set("Content-Type", contentType);

    const upstream = await fetch(target, {
      method: request.method,
      headers,
      body: request.method === "POST" ? await correctionBody(request) : undefined,
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
  } catch (error) {
    if (error instanceof ApiRequestError) {
      const headers = new Headers();
      if (error instanceof ArchiveRequestError && error.retryAfter) headers.set("Retry-After", error.retryAfter);
      return Response.json({ detail: error.status === 429 ? "Too many requests." : "Backend request failed." }, { status: error.status, headers });
    }
    if (error instanceof BodyTooLarge) {
      return Response.json({ detail: "Request body too large." }, { status: 413 });
    }
    return Response.json({ detail: "Backend service unavailable." }, { status: 502 });
  }
}

export const GET = proxy;
export const POST = proxy;
