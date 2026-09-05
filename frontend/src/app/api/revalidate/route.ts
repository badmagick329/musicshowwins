import { timingSafeEqual } from "node:crypto";
import { revalidateTag } from "next/cache";
import { publicArchiveCacheTag } from "@/lib/api-server";

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
  return Response.json({ revalidated: true });
}
