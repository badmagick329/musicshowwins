import type { Metadata } from "next";
import type { ReactNode } from "react";
import { QueryProvider } from "@/components/query-provider";
import { SiteFooter, SiteHeader } from "@/components/site-shell";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "KpopWins | K-pop Music Show Wins",
    template: "%s | KpopWins",
  },
  description: "Search K-pop music show wins by artist, song, show, or date. Coverage starts in 2014.",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body className="flex min-h-screen flex-col">
        <QueryProvider>
          <SiteHeader />
          <div className="flex-1">{children}</div>
          <SiteFooter />
        </QueryProvider>
      </body>
    </html>
  );
}
