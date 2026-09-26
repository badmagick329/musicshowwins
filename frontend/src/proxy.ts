import { NextResponse, type NextRequest } from "next/server";
import { getServerApiBaseUrl, internalRequestHeaders } from "@/lib/api-server";

// Artist pages stream behind a loading screen, so a redirect from the page can
// only reach browsers as a meta refresh. Old numeric links get a real 308 here.
export async function proxy(request: NextRequest) {
  const id = request.nextUrl.pathname.split("/")[2];
  const response = await fetch(`${getServerApiBaseUrl()}/artists/${id}`, { headers: internalRequestHeaders(), cache: "no-store" });
  if (!response.ok) return NextResponse.next();
  const { slug } = (await response.json()) as { slug: string };
  const target = request.nextUrl.clone();
  target.pathname = `/artists/${slug}`;
  return NextResponse.redirect(target, 308);
}

export const config = { matcher: "/artists/:id([0-9]+)" };
