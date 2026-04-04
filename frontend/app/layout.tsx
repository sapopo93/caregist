import type { Metadata } from "next";
import "./globals.css";
import Link from "next/link";
import CompareBar from "@/components/CompareBar";
import AuthNav from "@/components/AuthNav";
import CookieConsent from "@/components/CookieConsent";

export const metadata: Metadata = {
  title: "CareGist — UK Care Provider Directory",
  description:
    "Find and compare CQC-rated care homes, GP surgeries, dental practices, and home care agencies across England. Powered by Care Quality Commission data.",
  openGraph: {
    title: "CareGist — UK Care Provider Directory",
    description: "Find and compare CQC-rated care homes, GP surgeries, dental practices, and home care agencies across England.",
    siteName: "CareGist",
    type: "website",
    locale: "en_GB",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
        <link
          href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;800&family=Lora:ital,wght@0,400;0,500;1,400&family=DM+Sans:wght@300;400;500;600&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="min-h-screen flex flex-col">
        <header className="bg-bark text-cream px-6 py-4 relative">
          <div className="max-w-6xl mx-auto flex items-center justify-between">
            <Link href="/" className="flex items-center">
              <img src="/logo-lockup-reverse.svg" alt="CareGist" className="h-14 md:h-16 w-auto" />
            </Link>
            <AuthNav />
          </div>
        </header>

        <main className="flex-1">{children}</main>

        <CompareBar />
        <CookieConsent />

        <footer className="bg-charcoal text-stone px-6 py-8 text-sm">
          <div className="max-w-6xl mx-auto">
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
            <div className="flex flex-wrap gap-4 mt-4 text-dusk">
              <Link href="/privacy" className="underline hover:text-cream">Privacy Policy</Link>
              <Link href="/terms" className="underline hover:text-cream">Terms of Service</Link>
              <Link href="/acceptable-use" className="underline hover:text-cream">Acceptable Use</Link>
              <Link href="/review-policy" className="underline hover:text-cream">Review Policy</Link>
              <Link href="/cookies" className="underline hover:text-cream">Cookies</Link>
              <Link href="/pricing" className="underline hover:text-cream">Pricing</Link>
              <Link href="/api" className="underline hover:text-cream">API</Link>
              <Link href="/find-care" className="underline hover:text-cream">Find Care</Link>
              <Link href="/groups" className="underline hover:text-cream">Care Groups</Link>
              <Link href="/why-caregist" className="underline hover:text-cream">Why CareGist</Link>
              <a href="mailto:hello@caregist.co.uk" className="underline hover:text-cream">Contact</a>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
