"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

export default function AuthNav() {
  const router = useRouter();
  const [user, setUser] = useState<{ name: string } | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem("caregist_user");
    if (stored) {
      try { setUser(JSON.parse(stored)); } catch {}
    }
    const sync = () => {
      const s = localStorage.getItem("caregist_user");
      setUser(s ? JSON.parse(s) : null);
    };
    window.addEventListener("storage", sync);
    window.addEventListener("caregist_auth_change", sync);
    return () => {
      window.removeEventListener("storage", sync);
      window.removeEventListener("caregist_auth_change", sync);
    };
  }, []);

  const handleLogout = async () => {
    await fetch("/api/v1/auth/session", { method: "DELETE", credentials: "include" }).catch(() => {});
    localStorage.removeItem("caregist_user");
    localStorage.removeItem("caregist_tier");
    window.dispatchEvent(new Event("caregist_auth_change"));
    setUser(null);
    setMenuOpen(false);
    router.push("/");
  };

  const navLinks = (
    <>
      <Link href="/why-caregist" className="hover:text-amber transition-colors" onClick={() => setMenuOpen(false)}>Why CareGist</Link>
      <Link href="/search" className="hover:text-amber transition-colors" onClick={() => setMenuOpen(false)}>Lead Feed</Link>
      <Link href="/api" className="hover:text-amber transition-colors" onClick={() => setMenuOpen(false)}>API</Link>
      <Link href="/pricing" className="hover:text-amber transition-colors" onClick={() => setMenuOpen(false)}>Pricing</Link>
    </>
  );

  return (
    <>
      {/* Desktop nav */}
      <nav className="hidden md:flex gap-6 text-sm items-center">
        {navLinks}
        {user ? (
          <>
            <Link href="/dashboard" className="hover:text-amber transition-colors">Dashboard</Link>
            <button onClick={handleLogout} className="hover:text-amber transition-colors">Log Out</button>
          </>
        ) : (
          <>
            <Link href="/login" className="hover:text-amber transition-colors">Log In</Link>
            <Link href="/signup" className="px-4 py-1.5 bg-clay rounded-lg hover:bg-amber transition-colors">Sign Up</Link>
          </>
        )}
      </nav>

      {/* Mobile hamburger */}
      <button
        className="md:hidden p-2"
        onClick={() => setMenuOpen(!menuOpen)}
        aria-label={menuOpen ? "Close menu" : "Open menu"}
      >
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          {menuOpen ? (
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          ) : (
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
          )}
        </svg>
      </button>

      {/* Mobile menu dropdown */}
      {menuOpen && (
        <div className="md:hidden absolute top-full left-0 right-0 bg-bark border-t border-cream/10 px-6 py-4 flex flex-col gap-3 text-sm z-50">
          {navLinks}
          {user ? (
            <>
              <Link href="/dashboard" className="hover:text-amber transition-colors" onClick={() => setMenuOpen(false)}>Dashboard</Link>
              <button onClick={handleLogout} className="text-left hover:text-amber transition-colors">Log Out</button>
            </>
          ) : (
            <>
              <Link href="/login" className="hover:text-amber transition-colors" onClick={() => setMenuOpen(false)}>Log In</Link>
              <Link href="/signup" className="hover:text-amber transition-colors" onClick={() => setMenuOpen(false)}>Sign Up</Link>
            </>
          )}
        </div>
      )}
    </>
  );
}
