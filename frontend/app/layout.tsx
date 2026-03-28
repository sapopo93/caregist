import type { Metadata } from "next";
import "./globals.css";
import Link from "next/link";
import CompareBar from "@/components/CompareBar";

export const metadata: Metadata = {
  title: "CareGist — UK Care Provider Directory",
  description:
    "Find and compare CQC-rated care homes, GP surgeries, dental practices, and home care agencies across England. Powered by Care Quality Commission data.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;800&family=Lora:ital,wght@0,400;0,500;1,400&family=DM+Sans:wght@300;400;500;600&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="min-h-screen flex flex-col">
        <header className="bg-bark text-cream px-6 py-4">
          <div className="max-w-6xl mx-auto flex items-center justify-between">
            <Link href="/" className="text-2xl font-bold" style={{ fontFamily: "Playfair Display" }}>
              <span className="text-amber">C</span>are<span className="text-amber">G</span>ist
            </Link>
            <nav className="flex gap-6 text-sm items-center">
              <Link href="/search" className="hover:text-amber transition-colors">Search</Link>
              <Link href="/compare" className="hover:text-amber transition-colors">Compare</Link>
              <Link href="/pricing" className="hover:text-amber transition-colors">Pricing</Link>
              <Link href="/dashboard" className="hover:text-amber transition-colors">Dashboard</Link>
              <Link href="/signup" className="px-4 py-1.5 bg-clay rounded-lg hover:bg-amber transition-colors">Sign Up</Link>
            </nav>
          </div>
        </header>

        <main className="flex-1">{children}</main>

        <CompareBar />

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
          </div>
        </footer>
      </body>
    </html>
  );
}
