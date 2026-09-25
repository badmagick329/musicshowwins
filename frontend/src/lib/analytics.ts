type Plausible = ((event: string, options: { props: Record<string, string> }) => void) & { q?: unknown[] };

// Plausible loads deferred; queue events fired before it arrives so early clicks still count.
export function trackEvent(event: string, props: Record<string, string> = {}) {
  const analytics = window as Window & { plausible?: Plausible };
  analytics.plausible ??= Object.assign((...args: Parameters<Plausible>) => {
    analytics.plausible!.q!.push(args);
  }, { q: [] as unknown[] });
  analytics.plausible(event, { props });
}
