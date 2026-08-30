import { cn } from "@/lib/utils";

export function BrandMark({ className, label }: { className?: string; label?: string }) {
  return (
    <svg
      viewBox="0 0 36 36"
      className={cn("shrink-0", className)}
      role={label ? "img" : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
      focusable="false"
      shapeRendering="crispEdges"
      data-brand-mark
    >
      <path fill="var(--foreground)" d="M4 4h31v31H4z" />
      <path fill="var(--brand-pink)" stroke="var(--foreground)" strokeWidth="2" d="M1 1h31v31H1z" />
      <path fill="white" d="M8 7h5v8l8-8h6l-10 9 10 10h-6l-8-9v9H8z" />
    </svg>
  );
}
