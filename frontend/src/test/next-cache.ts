import { vi } from "vitest";

// Most unit tests exercise data loading without a running Next cache runtime.
// Cache behaviour itself is covered by archive-read.test.tsx's persistent mock.
vi.mock("next/cache", () => ({ unstable_cache: <T>(load: T) => load }));
