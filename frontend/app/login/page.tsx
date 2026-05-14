"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

function LoginForm() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [showResetBanner, setShowResetBanner] = useState(false);
  const [showSessionExpiredBanner, setShowSessionExpiredBanner] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    setShowResetBanner(params.get("reset") === "success");
    setShowSessionExpiredBanner(params.get("session") === "expired");
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const res = await fetch("/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        // credentials:include so the browser stores the HttpOnly cookie
        // that the backend sets on the Set-Cookie response header.
        credentials: "include",
        body: JSON.stringify({ email, password }),
      });

      const data = await res.json();

      if (!res.ok) {
        setError(data.detail || "Login failed.");
        return;
      }

      // Auth state is now carried entirely by the HttpOnly caregist_session
      // cookie — no localStorage writes.

      const params = new URLSearchParams(window.location.search);
      const next = params.get("next");
      const upgrade = params.get("upgrade");
      const providerTier = params.get("provider_tier");

      if (providerTier) {
        try {
          const claimsRes = await fetch("/api/v1/claims/my-providers", {
            credentials: "include",
          });
          const claimsData = await claimsRes.json();
          const providers: { slug: string }[] = claimsData.providers || [];
          if (providers.length > 0) {
            router.push(`/provider-dashboard/${providers[0].slug}?upgrade_tier=${providerTier}`);
          } else {
            router.push(`/search?claim_intent=${providerTier}`);
          }
        } catch {
          router.push(`/search?claim_intent=${providerTier}`);
        }
        return;
      }

      if (next) {
        router.push(decodeURIComponent(next));
        return;
      }

      router.push(upgrade ? `/pricing?highlight=${upgrade}` : "/dashboard");
    } catch {
      setError("Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-cream">
      <form
        onSubmit={handleSubmit}
        className="bg-white p-8 rounded-2xl shadow-sm border border-stone/30 w-full max-w-sm space-y-5"
      >
        <h1 className="text-2xl font-semibold text-graphite">Log in</h1>

        {showResetBanner && (
          <p className="text-sm text-green-700 bg-green-50 rounded-lg px-4 py-2">
            Password reset successful. You can now log in with your new password.
          </p>
        )}

        {showSessionExpiredBanner && (
          <p className="text-sm text-amber-700 bg-amber-50 rounded-lg px-4 py-2">
            Your session expired. Log in again to continue.
          </p>
        )}

        {error && (
          <p className="text-sm text-red-600 bg-red-50 rounded-lg px-4 py-2">{error}</p>
        )}

        <div>
          <label className="block text-sm font-medium text-graphite mb-1">
            Email
          </label>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full px-4 py-3 rounded-lg border border-stone bg-cream focus:ring-2 focus:ring-clay focus:outline-none"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-graphite mb-1">
            Password
          </label>
          <input
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full px-4 py-3 rounded-lg border border-stone bg-cream focus:ring-2 focus:ring-clay focus:outline-none"
          />
          <Link href="/forgot-password" className="text-xs text-clay hover:underline mt-1 inline-block">
            Forgot password?
          </Link>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-clay text-white py-3 rounded-lg font-medium hover:bg-clay/90 transition disabled:opacity-50"
        >
          {loading ? "Logging in..." : "Log In"}
        </button>

        <p className="text-sm text-center text-stone">
          Don&apos;t have an account?{" "}
          <Link href="/signup" className="text-clay hover:underline">
            Sign up
          </Link>
        </p>
      </form>
    </div>
  );
}

export default function LoginPage() {
  return <LoginForm />;
}
