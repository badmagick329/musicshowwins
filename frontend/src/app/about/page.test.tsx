import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/components/correction-form", () => ({ CorrectionForm: () => <form data-correction-form /> }));

import AboutPage from "./page";

afterEach(() => vi.unstubAllEnvs());

describe("AboutPage", () => {
  it("contains the public archive and correction copy", () => {
    vi.stubEnv("SUPPORT_URL", "https://support.example/kpopwins");
    const html = renderToStaticMarkup(<AboutPage />);
    expect(html).toContain("fan-made archive for exploring Korean music-show wins");
    expect(html).toContain("six weekly shows from 2014 onward");
    expect(html).toContain("compiled from Wikipedia and reviewed");
    expect(html).toContain("Report a correction");
    expect(html).toContain("data-correction-form");
    expect(html).not.toContain("Support KpopWins");
    expect(html).not.toContain("Buy me a coffee");
  });
});
