"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

export default function AuthNav() {
  const router = useRouter();
  const [user, setUser] = useState<{ name: string } | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);

  // Auth state comes from /api/v1/auth/whoami (HttpOnly cookie flow).
  // No localStorage reads — the cookie is sent automatically by the browser.
  useEffect(() => {
    let cancelled = false;
    fetch("/api/v1/auth/whoami", { credentials: "include" })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (!cancelled && data?.email) {
          setUser({ name: data.email });
        }
      })
      .catch(() => {});
    return () => { cancelled = true; };
  }, []);

  const handleLogout = async () => {
    await fetch("/api/v1/auth/logout", { method: "POST", credentials: "include" }).catch(() => {});
    setUser(null);
    setMenuOpen(false);
    router.push("/");
  };

  const navLinks = (
    <>
      <Link href="/why" onClick={() => setMenuOpen(false)}>Why CareGist</Link>
      <Link href="/lead-feed" onClick={() => setMenuOpen(false)}>Lead Feed</Link>
      <Link href="/api" onClick={() => setMenuOpen(false)}>API</Link>
      <Link href="/pricing" onClick={() => setMenuOpen(false)}>Pricing</Link>
    </>
  );

  return (
    <>
      {/* Desktop nav */}
      <nav className="hidden md:flex items-center gap-6 text-sm font-medium text-graphite">
        {navLinks}
        {user ? (
          <>
            <Link href="/dashboard">Dashboard</Link>
            <button onClick={handleLogout}>Log Out</button>
          </>
        ) : (
          <>
            <Link href="/login">Log In</Link>
            <Link href="/signup">Sign Up</Link>
          </>
        )}
      </nav>

      {/* Mobile hamburger */}
      <button
        className="md:hidden"
        onClick={() => setMenuOpen(!menuOpen)}
        aria-label={menuOpen ? "Close menu" : "Open menu"}
      >
        <span className="sr-only">{menuOpen ? "Close" : "Menu"}</span>
      </button>

      {/* Mobile menu dropdown */}
      {menuOpen && (
        <div className="absolute top-full left-0 right-0 bg-white border-t border-stone/20 p-4 flex flex-col gap-4 text-sm font-medium text-graphite md:hidden">
          {navLinks}
          {user ? (
            <>
              <Link href="/dashboard" onClick={() => setMenuOpen(false)}>Dashboard</Link>
              <button onClick={handleLogout}>Log Out</button>
            </>
          ) : (
            <>
              <Link href="/login" onClick={() => setMenuOpen(false)}>Log In</Link>
              <Link href="/signup" onClick={() => setMenuOpen(false)}>Sign Up</Link>
            </>
          )}
        </div>
      )}
    </>
  );
}
