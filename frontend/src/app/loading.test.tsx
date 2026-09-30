import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import ArtistsLoading from "./artists/(index)/loading";
import SongsLoading from "./songs/(index)/loading";
import WinsLoading from "./wins/loading";

describe("route loading messages", () => {
  it.each([
    [ArtistsLoading, "Loading artists…"],
    [SongsLoading, "Loading songs…"],
    [WinsLoading, "Loading wins…"],
  ])("renders the expected route-specific message", (Loading, message) => {
    expect(renderToStaticMarkup(<Loading />)).toContain(message);
  });
});
