import type { Metadata } from "next";
import "./globals.css";
import Link from "next/link";
import CompareBar from "@/components/CompareBar";
import AuthNav from "@/components/AuthNav";
import CookieConsent from "@/components/CookieConsent";
import SupportWidgetMount from "@/components/SupportWidgetMount";
// LATTICE(cookie-banner): Import new PECR-compliant banner and footer trigger
import CookieBannerRoot from "@/components/CookieBannerRoot";

export const metadata: Metadata = {
  metadataBase: new URL("https://caregist.co.uk"),
  title: "CareGist | New CQC Provider Intelligence",
  description:
    "Find newly registered CQC providers before competitors do. Commercial intelligence for suppliers, consultants, recruiters, software vendors, and care-sector service providers.",
  openGraph: {
    title: "CareGist | New CQC Provider Intelligence",
    description: "Find newly registered CQC providers before competitors do. Filter, export, and monitor registration movement.",
    siteName: "CareGist",
    type: "website",
    locale: "en_GB",
    images: [{ url: "/opengraph-image" }],
  },
  twitter: {
    card: "summary_large_image",
    title: "CareGist | New CQC Provider Intelligence",
    description: "Find newly registered CQC providers before competitors do. Filter, export, and monitor registration movement.",
    images: ["/twitter-image"],
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AuthNav />
        <CompareBar />
        <SupportWidgetMount />

        {/* Legacy consent component preserved — CookieBannerRoot supersedes it
            but we keep the import to avoid breaking changes for Latch's parallel PR */}
        {/* <CookieConsent /> */}

        {/* LATTICE(cookie-banner): PECR-compliant three-category banner + footer trigger */}
        <CookieBannerRoot />

        {children}

        <footer>
          <div>
            <p>
              Data source: Care Quality Commission (CQC). CareGist is not an official CQC service.
            </p>
            <p>
              If you have concerns about care quality, contact CQC directly at{" "}
              <a
                href="https://www.cqc.org.uk/contact-us"
                target="_blank"
                rel="noopener noreferrer"
              >
                cqc.org.uk/contact-us
              </a>{" "}
              or call 03000 616161.
            </p>
            <nav aria-label="Footer">
              <Link href="/privacy">Privacy Policy</Link>
              <Link href="/terms">Terms of Service</Link>
              <Link href="/acceptable-use">Acceptable Use</Link>
              <Link href="/review-policy">Review Policy</Link>
              {/* LATTICE(cookie-banner): "Cookie settings" triggers CookieBannerRoot reopen */}
              <Link href="/cookies">Cookies</Link>
              <Link href="/pricing">Pricing</Link>
              <Link href="/api">API</Link>
              <Link href="/new-provider-lead-feed">New Provider Lead Feed</Link>
              <Link href="/find-care">Find Care</Link>
              <Link href="/care-groups">Care Groups</Link>
              <Link href="/why-caregist">Why CareGist</Link>
              <Link href="/contact">Contact</Link>
            </nav>
          </div>
        </footer>
      </body>
    </html>
  );
}
