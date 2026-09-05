import { timingSafeEqual } from "node:crypto";
import { revalidateTag } from "next/cache";
import { publicArchiveCacheTag, warmCanonicalArchivePages } from "@/lib/api-server";

function validSecret(request: Request) {
  const configured = process.env.CACHE_REVALIDATION_SECRET;
  const supplied = request.headers.get("authorization")?.replace(/^Bearer\s+/i, "");
  if (!configured || !supplied) return false;
  const expected = Buffer.from(configured);
  const actual = Buffer.from(supplied);
  return expected.length === actual.length && timingSafeEqual(expected, actual);
}

export async function POST(request: Request) {
  if (!validSecret(request)) {
    return Response.json({ detail: "Unauthorized." }, { status: 401 });
  }
  revalidateTag(publicArchiveCacheTag, { expire: 0 });
  try {
    await warmCanonicalArchivePages();
    return Response.json({ revalidated: true, warmed: true });
  } catch {
    return Response.json(
      { detail: "Cache was invalidated, but canonical pages could not be warmed.", revalidated: true, warmed: false },
      { status: 502 },
    );
  }
}
