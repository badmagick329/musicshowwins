import type { Metadata } from "next";
import type { ReactNode } from "react";
import Script from "next/script";
import { QueryProvider } from "@/components/query-provider";
import { JsonLd } from "@/components/json-ld";
import { SiteFooter, SiteHeader } from "@/components/site-shell";
import { siteDescription, siteName, siteUrl } from "@/lib/seo";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: "KpopWins | K-pop Music Show Wins",
    template: "%s | KpopWins",
  },
  description: siteDescription,
  alternates: { canonical: "/" },
  openGraph: {
    type: "website",
    url: "/",
    siteName,
    title: "KpopWins | K-pop Music Show Wins",
    description: siteDescription,
  },
  twitter: {
    card: "summary_large_image",
    title: "KpopWins | K-pop Music Show Wins",
    description: siteDescription,
  },
  robots: { index: true, follow: true },
};

export const dynamic = "force-dynamic";

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <head>
        <link rel="describedby" href="/llms.txt" type="text/markdown" />
        <JsonLd data={{
          "@context": "https://schema.org",
          "@type": "WebSite",
          name: siteName,
          url: siteUrl,
          description: siteDescription,
          potentialAction: {
            "@type": "SearchAction",
            target: `${siteUrl}/?search={search_term_string}#search`,
            "query-input": "required name=search_term_string",
          },
        }} />
        <Script
          defer
          src="/ingest/js/script.js"
          data-domain="kpopwins.info"
          data-api="/ingest/api/event"
        />
      </head>
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
