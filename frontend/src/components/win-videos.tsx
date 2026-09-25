"use client";

import { useState } from "react";
import { ChevronDown, ExternalLink, Play, Search } from "lucide-react";
import type { Win, WinReference } from "@/lib/api-shared";
import { cn, formatDate } from "@/lib/utils";
import { trackEvent } from "@/lib/analytics";
import { TableCell, TableRow } from "@/components/ui/table";

export function winVideoReferences(win: Win) {
  return win.references.filter((reference) => reference.reference_type === "video");
}

export function winVideoActionLabel(count: number, isOfficial = true) {
  if (count > 1) return "Choose video";
  // Fan uploads can vanish or be edited, so visitors should know before leaving the site.
  return isOfficial ? "Watch video" : "Fan upload";
}

type VideoPlacement = "desktop" | "mobile" | "list";

// Measures whether visitors use video links at all, and whether fan uploads earn their removal risk.
function trackVideoOpened(win: Win, video: WinReference, placement: VideoPlacement) {
  trackEvent("Win video opened", {
    show: win.show.slug,
    year: win.date.slice(0, 4),
    source: video.is_official ? "official" : "fan",
    placement,
  });
}

function trackSearch(win: Win, placement: VideoPlacement) {
  trackEvent("YouTube search clicked", { show: win.show.slug, year: win.date.slice(0, 4), placement });
}

function winContext(win: Win) {
  return `${win.song.title} by ${win.song.artist.name}, ${formatDate(win.date)}, ${win.show.name}`;
}

const winVideoActionClass = "grid cursor-pointer grid-cols-[0.875rem_1fr_0.875rem] items-center gap-1.5 whitespace-nowrap border-2 border-foreground bg-action-pink font-bold text-primary-foreground transition-colors motion-reduce:transition-none hover:bg-accent-foreground";
const desktopActionClass = "h-8 px-2.5 text-xs shadow-[2px_2px_0_var(--foreground)]";
const mobileActionClass = "min-h-10 w-44 max-w-full px-3 text-sm shadow-[2px_2px_0_var(--foreground)]";

function YouTubeSearchLink({ win, placement, className }: { win: Win; placement: VideoPlacement; className?: string }) {
  const date = win.date.slice(2).replaceAll("-", "");
  const query = `${win.song.artist.name} ${win.song.title} ${date}`;
  const href = `https://www.youtube.com/results?${new URLSearchParams({ search_query: query })}`;
  return (
    <a href={href} target="_blank" rel="noopener noreferrer"
      onClick={() => trackSearch(win, placement)}
      aria-label={`Search YouTube for ${winContext(win)}`}
      className={cn("inline-flex min-h-11 items-center gap-1.5 text-xs text-muted-foreground underline underline-offset-4 hover:text-foreground focus-visible:outline-2 focus-visible:outline-offset-2", className)}>
      <Search className="size-3.5 shrink-0" aria-hidden="true" />
      <span>Search YouTube</span>
    </a>
  );
}

// Searching YouTube for a stage that never happened wastes the visitor's click.
function AbsentFromBroadcast({ className }: { className?: string }) {
  return <span className={cn("inline-flex min-h-11 items-center text-xs text-muted-foreground", className)}>Absent from broadcast</span>;
}

function NoVideo({ win, placement, className }: { win: Win; placement: VideoPlacement; className?: string }) {
  return win.performed === false ? <AbsentFromBroadcast className={className} /> : <YouTubeSearchLink win={win} placement={placement} className={className} />;
}

function WinVideoActionLink({ win, video, placement, className }: { win: Win; video: WinReference; placement: VideoPlacement; className: string }) {
  return (
    <a
      href={video.url}
      target="_blank"
      rel="noopener noreferrer"
      onClick={() => trackVideoOpened(win, video, placement)}
      aria-label={`Watch ${video.is_official ? "video" : "fan upload"} for ${winContext(win)}`}
      className={cn(winVideoActionClass, className)}
    >
      <Play className="size-3.5 shrink-0" aria-hidden="true" />
      <span className="text-center">{winVideoActionLabel(1, video.is_official)}</span>
      <ExternalLink className="size-3.5 shrink-0" aria-hidden="true" />
    </a>
  );
}

function WinVideoToggleButton({ win, count, open, panelId, onToggle, className }: { win: Win; count: number; open: boolean; panelId: string; onToggle: () => void; className: string }) {
  return (
    <button
      type="button"
      aria-expanded={open}
      aria-controls={panelId}
      aria-label={`Choose from ${count} videos for ${winContext(win)}`}
      onClick={onToggle}
      className={cn(winVideoActionClass, className)}
    >
      <Play className="size-3.5 shrink-0" aria-hidden="true" />
      <span className="text-center">{winVideoActionLabel(count)}</span>
      <ChevronDown aria-hidden="true" className={cn("size-3.5 shrink-0 transition-transform duration-150 motion-reduce:transition-none", open && "rotate-180")} />
    </button>
  );
}

function WinVideoLink({ win, video }: { win: Win; video: WinReference }) {
  const title = video.title.trim() || (video.is_official ? "Official video" : "Video");
  const publisher = video.publisher_name.trim() || "YouTube";
  return (
    <li>
      <a
        href={video.url}
        target="_blank"
        rel="noopener noreferrer"
        onClick={() => trackVideoOpened(win, video, "list")}
        className="flex items-center gap-3 border border-border bg-card px-3 py-2.5 text-foreground transition-colors motion-reduce:transition-none hover:bg-accent focus-visible:bg-accent"
      >
        <Play aria-hidden="true" className="size-5 shrink-0 text-brand-pink" />
        <span className="min-w-0 flex-1">
          <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <span className="break-words font-semibold leading-snug">{title}</span>
            {video.is_official && title !== "Official video" && (
              <span className="border border-border bg-secondary px-1.5 py-0.5 text-xs font-bold uppercase tracking-wide text-secondary-foreground">Official video</span>
            )}
            {!video.is_official && (
              <span className="border border-border bg-muted px-1.5 py-0.5 text-xs font-bold uppercase tracking-wide text-muted-foreground">Fan upload</span>
            )}
          </span>
          <span className="mt-0.5 block text-xs text-muted-foreground">{publisher}</span>
        </span>
        <ExternalLink aria-hidden="true" className="size-4 shrink-0 text-muted-foreground" />
      </a>
    </li>
  );
}

function WinVideoPanel({ win, videos, panelId }: { win: Win; videos: WinReference[]; panelId: string }) {
  return (
    <div id={panelId} className="border-l-4 border-brand-pink bg-highlight-yellow p-3">
      <ul aria-label={`Videos for ${winContext(win)}`} className="flex flex-col gap-2">
        {videos.map((video) => <WinVideoLink key={video.id} win={win} video={video} />)}
      </ul>
    </div>
  );
}

export function DesktopWinVideoRow({ win, colSpan, videoCellClassName = "w-44 px-4 py-3 text-right", compactAction = false, children }: { win: Win; colSpan: number; videoCellClassName?: string; compactAction?: boolean; children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  const videos = winVideoReferences(win);
  const panelId = `win-videos-desktop-${win.id}`;
  const actionClassName = cn(desktopActionClass, compactAction ? "ml-auto w-44 max-w-full" : "w-full");
  return (
    <>
      <TableRow className="border-border/70 hover:bg-accent/60">
        {children}
        <TableCell className={videoCellClassName}>
          {videos.length === 0 ? (
            <NoVideo win={win} placement="desktop" />
          ) : videos.length === 1 ? (
            <WinVideoActionLink win={win} video={videos[0]} placement="desktop" className={actionClassName} />
          ) : (
            <WinVideoToggleButton win={win} count={videos.length} open={open} panelId={panelId} onToggle={() => setOpen(!open)} className={actionClassName} />
          )}
        </TableCell>
      </TableRow>
      {open && videos.length > 1 && (
        <TableRow className="border-border/70 hover:bg-inherit">
          <TableCell colSpan={colSpan} className="p-0">
            <WinVideoPanel win={win} videos={videos} panelId={panelId} />
          </TableCell>
        </TableRow>
      )}
    </>
  );
}

export function MobileWinVideoDisclosure({ win, className }: { win: Win; className?: string }) {
  const [open, setOpen] = useState(false);
  const videos = winVideoReferences(win);
  const panelId = `win-videos-mobile-${win.id}`;
  if (!videos.length) return <div className={className}><NoVideo win={win} placement="mobile" className="text-sm" /></div>;
  return (
    <div className={cn("flex flex-col items-end", className)}>
      {videos.length === 1 ? (
        <WinVideoActionLink win={win} video={videos[0]} placement="mobile" className={mobileActionClass} />
      ) : (
        <>
          <WinVideoToggleButton win={win} count={videos.length} open={open} panelId={panelId} onToggle={() => setOpen(!open)} className={mobileActionClass} />
          {open && <div className="w-full pt-2"><WinVideoPanel win={win} videos={videos} panelId={panelId} /></div>}
        </>
      )}
    </div>
  );
}
