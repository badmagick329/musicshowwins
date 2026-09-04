import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/components/correction-form", () => ({ CorrectionForm: () => <form data-correction-form /> }));

import AboutPage from "./page";

afterEach(() => vi.unstubAllEnvs());

describe("AboutPage", () => {
  it("contains the public archive and correction copy", () => {
    vi.stubEnv("SUPPORT_URL", "https://support.example/kpopwins");
    const html = renderToStaticMarkup(<AboutPage />);
    expect(html).toContain("KpopWins is a fan-made record of K-pop music show wins. It covers six weekly shows from 2014 onward. KpopWins uses Wikipedia as its source and reviews results before publication.");
    expect(html).not.toContain("older records may be incomplete or disputed");
    expect(html).toContain("Your feedback helps us decide what to improve next.");
    expect(html).toContain("Share feedback");
    expect(html).toContain("data-correction-form");
    expect(html).not.toContain("Support KpopWins");
    expect(html).not.toContain("Buy me a coffee");
  });
});
