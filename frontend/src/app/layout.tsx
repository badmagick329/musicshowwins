import type { Metadata } from "next";
import type { ReactNode } from "react";
import { QueryProvider } from "@/components/query-provider";
import { SiteFooter, SiteHeader } from "@/components/site-shell";
import "./globals.css";

export const metadata: Metadata = {
  title: "KpopWins — Music show wins, clearly kept",
  description: "Explore K-pop music show wins from 2014 onward.",
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
