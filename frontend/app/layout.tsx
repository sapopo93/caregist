import type { Metadata } from "next";
import Link from "next/link";
import localFont from "next/font/local";
import { unstable_cache } from "next/cache";
import { connection } from "next/server";

import "./globals.css";

import AuthNav from "@/components/AuthNav";
import CompareBar from "@/components/CompareBar";
import CommandPalette from "@/components/CommandPalette";
import PaletteHint from "@/components/PaletteHint";
import CookieConsent from "@/components/CookieConsent";
import SupportWidgetMount from "@/components/SupportWidgetMount";

import { getServerApiBase } from "@/lib/server-api-config";

const SITE_URL = "https://www.caregist.co.uk";

const getDataCurrentAsOf = unstable_cache(async (): Promise<string | null> => {
  try {
    const apiBase = getServerApiBase();
    const response = await fetch(`${apiBase}/api/v1/health/freshness`, {
      next: { revalidate: 3600 },
      signal: AbortSignal.timeout(5000),
    });
    if (!response.ok) return null;
    const data = await response.json();
    if (data?.status !== "fresh") return null;
    const retrievedAt = data?.sourceRetrievedAt;
    if (!retrievedAt) return null;
    const retrieved = new Date(retrievedAt);
    if (Number.isNaN(retrieved.getTime())) return null;
    return retrieved.toLocaleString("en-GB", {
      dateStyle: "long",
      timeStyle: "short",
      timeZone: "UTC",
    });
  } catch {
    return null;
  }
}, ["caregist-data-current-as-of"], { revalidate: 3600 });

type FreshnessChip = { state: "fresh" | "not-fresh"; label: string } | null;

/** Header trust chip. Unlike the footer line it also reports a non-fresh source, so staleness is never hidden.
 *  Relies on fetch revalidation (1h) rather than unstable_cache so a transient failure is not cached as "no data". */
async function getFreshnessChip(): Promise<FreshnessChip> {
  try {
    const response = await fetch(`${getServerApiBase()}/api/v1/health/freshness`, {
      next: { revalidate: 3600 },
      signal: AbortSignal.timeout(5000),
    });
    if (response.status !== 200 && response.status !== 503) return null;
    const data = await response.json();
    if (data?.status !== "fresh") return { state: "not-fresh", label: "Check data status" };
    const retrieved = new Date(data?.sourceRetrievedAt);
    if (Number.isNaN(retrieved.getTime())) return null;
    const day = retrieved.toLocaleDateString("en-GB", { day: "numeric", month: "short", timeZone: "UTC" });
    return { state: "fresh", label: `Data as of ${day}` };
  } catch {
    return null;
  }
}

const dmSans = localFont({
  src: "./fonts/dm-sans-latin-wght-normal.woff2",
  weight: "300 600",
  variable: "--font-dm-sans",
  display: "swap",
  fallback: ["system-ui", "sans-serif"],
  adjustFontFallback: "Arial",
});

const playfairDisplay = localFont({
  src: "./fonts/playfair-display-latin-wght-normal.woff2",
  weight: "700 800",
  variable: "--font-playfair-display",
  display: "swap",
  fallback: ["Georgia", "serif"],
  adjustFontFallback: "Times New Roman",
});

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: "CareGist | CQC Signal Intelligence",
  description:
    "Search CQC-registered services for free and turn verified new registrations and rating changes into evidence-linked team workflows.",
  icons: {
    icon: [{ url: "/favicon.svg", type: "image/svg+xml" }],
  },
  openGraph: {
    title: "CareGist | CQC Signal Intelligence",
    description:
      "Verified CQC new registrations and rating changes with traceable source evidence.",
    siteName: "CareGist",
    type: "website",
    locale: "en_GB",
    images: [{ url: "/opengraph-image" }],
  },
  twitter: {
    card: "summary_large_image",
    title: "CareGist | CQC Signal Intelligence",
    description:
      "Verified CQC new registrations and rating changes with traceable source evidence.",
    images: ["/twitter-image"],
  },
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  await connection();
  const dataCurrentAsOf = await getDataCurrentAsOf();
  const freshnessChip = await getFreshnessChip();

  return (
    <html lang="en" className={`${dmSans.variable} ${playfairDisplay.variable}`}>
      <head>
        <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
      </head>
      <body className="flex min-h-screen flex-col">
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[60] focus:rounded-lg focus:bg-cream focus:px-4 focus:py-2 focus:text-sm focus:font-semibold focus:text-bark focus:shadow-lg"
        >
          Skip to main content
        </a>
        <header className="sticky top-0 z-40 border-b border-charcoal/30 bg-bark px-6 py-2.5 text-cream shadow-sm">
          <div className="mx-auto flex max-w-6xl items-center justify-between gap-4">
            <Link href="/" className="flex items-center">
              <img src="/logo-lockup-reverse.svg" alt="CareGist" className="h-9 w-auto md:h-10" />
            </Link>

            <form action="/search" method="get" role="search" className="relative hidden min-w-0 flex-1 md:block lg:max-w-sm">
              <label htmlFor="site-search" className="sr-only">Search care providers by name, town or postcode</label>
              <input
                id="site-search"
                name="q"
                type="search"
                placeholder="Search providers by name, town or postcode"
                className="h-9 w-full rounded-full border border-cream/20 bg-charcoal/40 px-4 pr-14 text-sm text-cream placeholder:text-cream/60 focus:border-amber focus:bg-charcoal/60 focus:outline-none"
              />
              <PaletteHint />
            </form>

            {freshnessChip ? (
              <Link
                href="/data-status"
                title="Open Data Status for the source dates behind every figure"
                className="hidden shrink-0 items-center gap-2 whitespace-nowrap rounded-full border border-cream/25 px-3 py-1 text-xs text-cream/90 transition hover:border-amber hover:text-amber xl:inline-flex"
              >
                <span aria-hidden className={`h-2 w-2 rounded-full ${freshnessChip.state === "fresh" ? "bg-sage" : "bg-amber"}`} />
                {freshnessChip.label}
              </Link>
            ) : null}

            <div className="flex items-center justify-end gap-3">
              <Link href="/pricing/territory" className="cta-primary cta-primary--sm whitespace-nowrap !gap-1 !px-3 !text-[0.8rem] md:hidden">
                Check territory
              </Link>
              <nav aria-label="Primary" className="hidden items-center gap-5 text-sm font-medium md:flex">
                <Link href="/search" className="hover:text-amber">
                  Directory
                </Link>
                <Link href="/pricing" className="hover:text-amber">
                  Products
                </Link>
                <Link href="/why-caregist" className="hover:text-amber">
                  About
                </Link>
                <Link href="/pricing/territory" className="cta-primary cta-primary--sm">
                  Check your territory
                </Link>
              </nav>
              <AuthNav />
            </div>
          </div>
        </header>

        <main id="main-content" tabIndex={-1} className="flex-1 focus:outline-none">{children}</main>

        <CommandPalette />
        <CompareBar />
        <CookieConsent />
        <SupportWidgetMount />

        <footer className="bg-charcoal px-6 py-8 text-sm text-stone">
          <div className="mx-auto max-w-6xl">
            <p className="mb-2">
              Contains public sector information licensed under the{" "}
              <a
                href="https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/"
                className="underline hover:text-cream"
                target="_blank"
                rel="noopener noreferrer"
              >
                Open Government Licence v3.0
              </a>
              .
            </p>
            {dataCurrentAsOf && (
              <p className="mb-2 text-dusk">
                Data current as of {dataCurrentAsOf} UTC.
              </p>
            )}
            <p className="mb-2 text-stone">
              CareGist is not an official CQC service.
            </p>
            <p className="text-stone">
              If you have concerns about care quality, contact CQC directly at{" "}
              <a href="https://www.cqc.org.uk/contact-us" className="underline hover:text-cream">
                cqc.org.uk/contact-us
              </a>{" "}
              or call 03000 616161.
            </p>
            <nav aria-label="Footer" className="mt-8 grid gap-8 border-t border-stone/20 pt-8 sm:grid-cols-2 lg:grid-cols-4">
              <div>
                <p className="mb-3 font-mono text-xs uppercase tracking-[0.18em] text-amber">Products</p>
                <ul className="space-y-2">
                  <li><Link href="/pricing" className="hover:text-cream hover:underline">Pricing</Link></li>
                  <li><Link href="/pricing/territory" className="hover:text-cream hover:underline">Check your territory</Link></li>
                  <li><Link href="/why-caregist" className="hover:text-cream hover:underline">Why CareGist</Link></li>
                </ul>
              </div>
              <div>
                <p className="mb-3 font-mono text-xs uppercase tracking-[0.18em] text-amber">Directory</p>
                <ul className="space-y-2">
                  <li><Link href="/search" className="hover:text-cream hover:underline">Search providers</Link></li>
                  <li><Link href="/find-care" className="hover:text-cream hover:underline">Find care</Link></li>
                  <li><Link href="/data-status" className="hover:text-cream hover:underline">Data status</Link></li>
                </ul>
              </div>
              <div>
                <p className="mb-3 font-mono text-xs uppercase tracking-[0.18em] text-amber">Legal</p>
                <ul className="space-y-2">
                  <li><Link href="/privacy" className="hover:text-cream hover:underline">Privacy Policy</Link></li>
                  <li><Link href="/terms" className="hover:text-cream hover:underline">Terms of Service</Link></li>
                  <li><Link href="/acceptable-use" className="hover:text-cream hover:underline">Acceptable Use</Link></li>
                  <li><Link href="/cookies" className="hover:text-cream hover:underline">Cookies</Link></li>
                </ul>
              </div>
              <div>
                <p className="mb-3 font-mono text-xs uppercase tracking-[0.18em] text-amber">Contact</p>
                <ul className="space-y-2">
                  <li><a href="mailto:support@caregist.co.uk" className="hover:text-cream hover:underline">support@caregist.co.uk</a></li>
                </ul>
              </div>
            </nav>
          </div>
        </footer>
      </body>
    </html>
  );
}
