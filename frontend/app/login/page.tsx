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

  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    setShowResetBanner(params.get("reset") === "success");
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const res = await fetch("/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      const data = await res.json();

      if (!res.ok) {
        setError(data.detail || "Login failed.");
        return;
      }

      localStorage.setItem("caregist_api_key", data.api_key);
      localStorage.setItem("caregist_user", JSON.stringify(data.user));
      localStorage.setItem("caregist_tier", data.tier);
      window.dispatchEvent(new Event("caregist_auth_change"));

      const upgrade = new URLSearchParams(window.location.search).get("upgrade");
      router.push(upgrade ? `/pricing?highlight=${upgrade}` : "/dashboard");
    } catch {
      setError("Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto px-6 py-16">
      <h1 className="text-3xl font-bold text-center mb-8">Log in</h1>

      {showResetBanner && (
        <div className="bg-cream border border-green-500 rounded-lg p-3 mb-4 text-sm text-green-700">
          Password reset successful. You can now log in with your new password.
        </div>
      )}

      {error && (
        <div className="bg-cream border border-alert rounded-lg p-3 mb-4 text-sm text-alert">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="email" className="block text-sm font-medium text-bark mb-1">Email</label>
          <input
            id="email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full px-4 py-3 rounded-lg border border-stone bg-cream focus:ring-2 focus:ring-clay focus:outline-none"
          />
        </div>
        <div>
          <label htmlFor="password" className="block text-sm font-medium text-bark mb-1">Password</label>
          <input
            id="password"
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full px-4 py-3 rounded-lg border border-stone bg-cream focus:ring-2 focus:ring-clay focus:outline-none"
          />
          <div className="text-right mt-1">
            <Link href="/forgot-password" className="text-sm text-clay underline">Forgot password?</Link>
          </div>
        </div>
        <button
          type="submit"
          disabled={loading}
          className="w-full py-3 bg-clay text-white rounded-lg font-medium hover:bg-bark transition-colors disabled:opacity-50"
        >
          {loading ? "Logging in..." : "Log In"}
        </button>
      </form>

      <p className="text-center text-sm text-dusk mt-6">
        Don&apos;t have an account? <Link href="/signup" className="text-clay underline">Sign up</Link>
      </p>
    </div>
  );
}

export default function LoginPage() {
  return <LoginForm />;
}
