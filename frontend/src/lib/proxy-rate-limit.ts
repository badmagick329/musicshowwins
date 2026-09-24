export const WINDOW_MS = 60_000;
export const MAX_REQUESTS = 120;
export const MAX_CLIENTS = 10_000;

let windowStart = 0;
const counts = new Map<string, number>();

export function resetProxyRateLimit() {
  counts.clear();
  windowStart = 0;
}

export function checkProxyRateLimit(clientIp: string, now = Date.now()) {
  const currentWindowStart = Math.floor(now / WINDOW_MS) * WINDOW_MS;
  if (currentWindowStart !== windowStart) {
    counts.clear();
    windowStart = currentWindowStart;
  }

  if (!counts.has(clientIp) && counts.size >= MAX_CLIENTS) {
    const oldestClientIp = counts.keys().next().value;
    if (oldestClientIp !== undefined) counts.delete(oldestClientIp);
  }

  const count = counts.get(clientIp) ?? 0;
  if (count >= MAX_REQUESTS) {
    return { allowed: false, retryAfter: Math.max(1, Math.ceil((windowStart + WINDOW_MS - now) / 1000)) };
  }

  counts.set(clientIp, count + 1);
  return { allowed: true, retryAfter: 0 };
}
