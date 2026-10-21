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
  const actions = new URL(request.url).searchParams.getAll("action");
  if (actions.length !== 1 || (actions[0] !== "invalidate" && actions[0] !== "warm")) {
    return Response.json({ detail: "Invalid cache action." }, { status: 400 });
  }
  if (actions[0] === "invalidate") {
    // Next applies tag invalidation when this request finishes. Warming must
    // happen in the caller's next request so it survives that invalidation.
    revalidateTag(publicArchiveCacheTag, { expire: 0 });
    return Response.json({ revalidated: true });
  }
  try {
    await warmCanonicalArchivePages();
    return Response.json({ warmed: true });
  } catch {
    return Response.json(
      { detail: "Canonical pages could not be warmed.", warmed: false },
      { status: 502 },
    );
  }
}
