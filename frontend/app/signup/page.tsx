"use client";

import { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";

function SignupForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const plan = searchParams.get("plan") || "free";

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // Redirect logged-in users to pricing (for upgrades) or dashboard
  useEffect(() => {
    const stored = localStorage.getItem("caregist_user");
    if (stored) {
      router.replace(plan !== "free" ? `/pricing` : "/dashboard");
    }
  }, [plan, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const res = await fetch("/api/v1/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, name, password }),
      });

      const data = await res.json();

      if (!res.ok) {
        setError(data.detail || "Registration failed.");
        return;
      }

      // Store API key in localStorage for dashboard
      localStorage.setItem("caregist_api_key", data.api_key);
      localStorage.setItem("caregist_user", JSON.stringify(data.user));
      localStorage.setItem("caregist_tier", data.tier);
      window.dispatchEvent(new Event("caregist_auth_change"));

      // If paid plan, redirect to checkout
      if (plan !== "free") {
        const checkoutRes = await fetch("/api/v1/billing/checkout", {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-API-Key": data.api_key },
          body: JSON.stringify({ email, tier: plan }),
        });
        const checkoutData = await checkoutRes.json();
        if (checkoutData.checkout_url) {
          window.location.href = checkoutData.checkout_url;
          return;
        }
      }

      router.push("/dashboard");
    } catch {
      setError("Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto px-6 py-16">
      <h1 className="text-3xl font-bold text-center mb-2">Create your account</h1>
      <p className="text-dusk text-center mb-8">
        {plan === "free" ? "Get a free API key instantly." : `Sign up for the ${plan} plan.`}
      </p>

      {error && (
        <div className="bg-cream border border-alert rounded-lg p-3 mb-4 text-sm text-alert">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="name" className="block text-sm font-medium text-bark mb-1">Name</label>
          <input
            id="name"
            type="text"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full px-4 py-3 rounded-lg border border-stone bg-cream focus:ring-2 focus:ring-clay focus:outline-none"
          />
        </div>
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
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full px-4 py-3 rounded-lg border border-stone bg-cream focus:ring-2 focus:ring-clay focus:outline-none"
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className="w-full py-3 bg-clay text-white rounded-lg font-medium hover:bg-bark transition-colors disabled:opacity-50"
        >
          {loading ? "Creating account..." : "Create Account"}
        </button>
      </form>

      <p className="text-center text-sm text-dusk mt-6">
        Already have an account? <Link href="/login" className="text-clay underline">Log in</Link>
      </p>
    </div>
  );
}

export default function SignupPage() {
  return (
    <Suspense fallback={<div className="max-w-md mx-auto px-6 py-16 text-center">Loading...</div>}>
      <SignupForm />
    </Suspense>
  );
}
