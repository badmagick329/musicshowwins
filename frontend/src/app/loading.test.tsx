import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import RootLoading from "./loading";
import ArtistsLoading from "./artists/loading";
import ArtistLoading from "./artists/[id]/loading";
import SongsLoading from "./songs/loading";
import SongLoading from "./songs/[id]/loading";
import WinsLoading from "./wins/loading";

describe("route loading messages", () => {
  it.each([
    [RootLoading, "Loading KpopWins…"],
    [ArtistsLoading, "Loading artists…"],
    [ArtistLoading, "Loading artist…"],
    [SongsLoading, "Loading songs…"],
    [SongLoading, "Loading song…"],
    [WinsLoading, "Loading wins…"],
  ])("renders the expected route-specific message", (Loading, message) => {
    expect(renderToStaticMarkup(<Loading />)).toContain(message);
  });
});
