import type { Metadata } from "next";
import Link from "next/link";

import "./globals.css";

import AuthNav from "@/components/AuthNav";
import CompareBar from "@/components/CompareBar";
import CookieConsent from "@/components/CookieConsent";
import SupportWidgetMount from "@/components/SupportWidgetMount";

const SITE_URL = "https://caregist.co.uk";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: "CareGist | CQC Data, Lead Lists, API & Provider Listings",
  description:
    "Search active CQC providers, request filtered lead lists, buy dataset packs, start new-provider intelligence plans, and upgrade provider listings.",
  openGraph: {
    title: "CareGist | CQC Data, Lead Lists, API & Provider Listings",
    description:
      "Search active CQC providers, request filtered lead lists, buy dataset packs, start new-provider intelligence plans, and upgrade provider listings.",
    siteName: "CareGist",
    type: "website",
    locale: "en_GB",
    images: [{ url: "/opengraph-image" }],
  },
  twitter: {
    card: "summary_large_image",
    title: "CareGist | CQC Data, Lead Lists, API & Provider Listings",
    description:
      "Search active CQC providers, request filtered lead lists, buy dataset packs, start new-provider intelligence plans, and upgrade provider listings.",
    images: ["/twitter-image"],
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const stripePaymentLink = process.env.STRIPE_PAYMENT_LINK_URL?.trim() || null;

  return (
    <html lang="en">
      <head>
        <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
        <link
          href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;800&family=Lora:ital,wght@0,400;0,500;1,400&family=DM+Sans:wght@300;400;500;600&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="flex min-h-screen flex-col">
        <header className="border-b border-stone bg-bark px-6 py-4 text-cream">
          <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4">
            <Link href="/" className="flex items-center">
              <img src="/logo-lockup-reverse.svg" alt="CareGist" className="h-12 w-auto md:h-14" />
            </Link>

            <div className="flex flex-wrap items-center justify-end gap-4">
              <nav className="flex flex-wrap items-center gap-5 text-sm font-medium">
                <Link href="/#products" className="hover:text-amber">
                  Products
                </Link>
                <Link href="/#positioning" className="hover:text-amber">
                  Who it's for
                </Link>
                <Link href="/why-caregist" className="hover:text-amber">
                  About
                </Link>
                <Link href="/search" className="hover:text-amber">
                  Search
                </Link>
                <Link href="/pricing" className="hover:text-amber">
                  Pricing
                </Link>
                <Link href="/api" className="hover:text-amber">
                  API
                </Link>
                <Link href="/lead-list" className="hover:text-amber">
                  Get a lead list
                </Link>
                <a
                  href={stripePaymentLink ?? "/lead-list"}
                  target={stripePaymentLink ? "_blank" : undefined}
                  rel={stripePaymentLink ? "noreferrer noopener" : undefined}
                  className="rounded-full bg-amber px-4 py-2 text-sm font-semibold text-charcoal transition hover:bg-cream"
                >
                  Buy dataset
                </a>
              </nav>
              <AuthNav />
            </div>
          </div>
        </header>

        <main className="flex-1">{children}</main>

        <CompareBar />
        <CookieConsent />
        <SupportWidgetMount />

        <footer className="bg-charcoal px-6 py-8 text-sm text-stone">
          <div className="mx-auto max-w-6xl">
            <p className="mb-2">
              Data source: Care Quality Commission (CQC). CareGist is not an official CQC service.
            </p>
            <p className="text-dusk">
              If you have concerns about care quality, contact CQC directly at{" "}
              <a href="https://www.cqc.org.uk/contact-us" className="underline hover:text-cream">
                cqc.org.uk/contact-us
              </a>{" "}
              or call 03000 616161.
            </p>
            <div className="mt-4 flex flex-wrap gap-4 text-dusk">
              <Link href="/privacy" className="underline hover:text-cream">
                Privacy Policy
              </Link>
              <Link href="/terms" className="underline hover:text-cream">
                Terms of Service
              </Link>
              <Link href="/acceptable-use" className="underline hover:text-cream">
                Acceptable Use
              </Link>
              <Link href="/review-policy" className="underline hover:text-cream">
                Review Policy
              </Link>
              <Link href="/cookies" className="underline hover:text-cream">
                Cookies
              </Link>
              <Link href="/search" className="underline hover:text-cream">
                Search
              </Link>
              <Link href="/find-care" className="underline hover:text-cream">
                Find Care
              </Link>
              <Link href="/groups" className="underline hover:text-cream">
                Care Groups
              </Link>
              <Link href="/pricing" className="underline hover:text-cream">
                Pricing
              </Link>
              <Link href="/api" className="underline hover:text-cream">
                API
              </Link>
              <Link href="/why-caregist" className="underline hover:text-cream">
                Why CareGist
              </Link>
              <Link href="/lead-list" className="underline hover:text-cream">
                Get a lead list
              </Link>
              <a href="mailto:hello@caregist.co.uk" className="underline hover:text-cream">
                Contact
              </a>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
