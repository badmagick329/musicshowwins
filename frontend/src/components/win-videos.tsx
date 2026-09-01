"use client";

import { useState } from "react";
import { ChevronDown, ExternalLink, Play } from "lucide-react";
import type { Win, WinReference } from "@/lib/api-shared";
import { cn, formatDate } from "@/lib/utils";
import { TableCell, TableRow } from "@/components/ui/table";

export function winVideoReferences(win: Win) {
  return win.references.filter((reference) => reference.reference_type === "video");
}

export function winVideoActionLabel(count: number) {
  return count === 1 ? "Watch video" : "Choose video";
}

function winContext(win: Win) {
  return `${win.song.title} by ${win.song.artist.name}, ${formatDate(win.date)}, ${win.show.name}`;
}

const winVideoActionClass = "grid w-full cursor-pointer grid-cols-[0.875rem_1fr_0.875rem] items-center gap-1.5 whitespace-nowrap border-2 border-foreground bg-brand-pink font-bold text-primary-foreground transition-colors motion-reduce:transition-none hover:bg-accent-foreground";
const desktopActionClass = "h-8 px-2.5 text-xs shadow-[2px_2px_0_var(--foreground)]";
const mobileActionClass = "min-h-11 px-4 text-sm shadow-[2px_2px_0_var(--foreground)]";

function WinVideoActionLink({ win, video, className }: { win: Win; video: WinReference; className: string }) {
  return (
    <a
      href={video.url}
      target="_blank"
      rel="noopener noreferrer"
      aria-label={`Watch video for ${winContext(win)}`}
      className={cn(winVideoActionClass, className)}
    >
      <Play className="size-3.5 shrink-0" aria-hidden="true" />
      <span className="text-center">{winVideoActionLabel(1)}</span>
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

function WinVideoLink({ video }: { video: WinReference }) {
  const title = video.title.trim() || (video.is_official ? "Official video" : "Video");
  const publisher = video.publisher_name.trim() || "YouTube";
  return (
    <li>
      <a
        href={video.url}
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center gap-3 border border-border bg-card px-3 py-2.5 text-foreground transition-colors motion-reduce:transition-none hover:bg-accent focus-visible:bg-accent"
      >
        <Play aria-hidden="true" className="size-5 shrink-0 text-brand-pink" />
        <span className="min-w-0 flex-1">
          <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <span className="break-words font-semibold leading-snug">{title}</span>
            {video.is_official && title !== "Official video" && (
              <span className="border border-border bg-secondary px-1.5 py-0.5 text-xs font-bold uppercase tracking-wide text-secondary-foreground">Official video</span>
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
        {videos.map((video) => <WinVideoLink key={video.id} video={video} />)}
      </ul>
    </div>
  );
}

export function DesktopWinVideoRow({ win, colSpan, videoCellClassName = "w-44 px-4 py-3 text-right", children }: { win: Win; colSpan: number; videoCellClassName?: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  const videos = winVideoReferences(win);
  const panelId = `win-videos-desktop-${win.id}`;
  return (
    <>
      <TableRow className="border-border/70 hover:bg-accent/60">
        {children}
        <TableCell className={videoCellClassName}>
          {videos.length === 0 ? (
            <span aria-hidden="true" className="text-muted-foreground">—</span>
          ) : videos.length === 1 ? (
            <WinVideoActionLink win={win} video={videos[0]} className={desktopActionClass} />
          ) : (
            <WinVideoToggleButton win={win} count={videos.length} open={open} panelId={panelId} onToggle={() => setOpen(!open)} className={desktopActionClass} />
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
  if (!videos.length) return null;
  return (
    <div className={className}>
      {videos.length === 1 ? (
        <WinVideoActionLink win={win} video={videos[0]} className={mobileActionClass} />
      ) : (
        <>
          <WinVideoToggleButton win={win} count={videos.length} open={open} panelId={panelId} onToggle={() => setOpen(!open)} className={mobileActionClass} />
          {open && <div className="pt-2"><WinVideoPanel win={win} videos={videos} panelId={panelId} /></div>}
        </>
      )}
    </div>
  );
}
