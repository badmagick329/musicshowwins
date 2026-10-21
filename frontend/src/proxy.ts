import { NextResponse, type NextRequest } from "next/server";
import { getServerApiBaseUrl } from "@/lib/api-server";
import { ArchiveRequestError, readPublicArchiveUncached } from "@/lib/archive-read";
import { ApiRequestError } from "@/lib/api-shared";

// Artist pages stream behind a loading screen, so a redirect from the page can
// only reach browsers as a meta refresh. Old numeric links get a real 308 here.
export async function proxy(request: NextRequest) {
  const id = request.nextUrl.pathname.split("/")[2];
  let data: unknown;
  try {
    data = (await readPublicArchiveUncached(`${getServerApiBaseUrl()}/artists/${id}`, request.signal)).data;
  } catch (error) {
    if (error instanceof ApiRequestError && error.status === 404) return NextResponse.next();
    if (error instanceof ArchiveRequestError && error.status === 429) {
      return NextResponse.json({ detail: "Too many requests." }, {
        status: 429, headers: error.retryAfter ? { "Retry-After": error.retryAfter } : undefined,
      });
    }
    throw error;
  }
  const slug = data && typeof data === "object" && "slug" in data ? data.slug : undefined;
  if (typeof slug !== "string" || !/^[a-z0-9_-]{1,200}$/.test(slug)) throw new Error("API returned an invalid artist slug.");
  const target = request.nextUrl.clone();
  target.pathname = `/artists/${slug}`;
  return NextResponse.redirect(target, 308);
}

export const config = { matcher: "/artists/:id([0-9]+)" };
