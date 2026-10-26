"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

export default function ForgotPasswordPage() {
  const router = useRouter();
  const [step, setStep] = useState<1 | 2>(1);
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleRequestCode = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const res = await fetch("/api/v1/auth/forgot-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setError(data.detail || "Request failed.");
        return;
      }

      setStep(2);
    } catch {
      setError("Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const res = await fetch("/api/v1/auth/reset-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, token: code.trim(), new_password: newPassword }),
      });

      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        setError(data.detail || "Reset failed.");
        return;
      }

      router.push("/login?reset=success");
    } catch {
      setError("Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto px-6 py-16">
      <h1 className="text-3xl font-bold text-center mb-2">Reset your password</h1>
      {step === 1 ? (
        <p className="text-dusk text-center mb-8">
          Enter the email you use to log in. We will email you a reset code.
        </p>
      ) : (
        <div className="bg-cream border border-stone rounded-lg p-4 mb-6 text-sm text-bark">
          <p className="font-medium mb-2">Check your email (including spam) for a message from CareGist.</p>
          <ol className="list-decimal pl-5 space-y-1">
            <li>Copy the whole reset code from the email. It is one long line with no spaces.</li>
            <li>Paste it into the <strong>Reset code</strong> box below.</li>
            <li>Choose a new password of at least 12 characters.</li>
            <li>Press <strong>Reset Password</strong>, then log in with your new password.</li>
          </ol>
          <p className="mt-2 text-dusk">
            The code expires after 15 minutes. If you asked for more than one code, use the newest email.
            No email after a few minutes? <button type="button" onClick={() => { setStep(1); setCode(""); setError(""); }} className="underline">Send a new code</button>.
          </p>
        </div>
      )}

      {error && (
        <div className="bg-cream border border-alert rounded-lg p-3 mb-4 text-sm text-alert">
          {error}
        </div>
      )}

      {step === 1 ? (
        <form onSubmit={handleRequestCode} className="space-y-4">
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-bark mb-1">Email</label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-4 py-3 rounded-lg border border-stone bg-cream focus:ring-2 focus:ring-clay focus:outline-none"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-clay text-white rounded-lg font-medium hover:bg-bark transition-colors disabled:opacity-50"
          >
            {loading ? "Sending..." : "Send Reset Code"}
          </button>
        </form>
      ) : (
        <form onSubmit={handleResetPassword} className="space-y-4">
          <div>
            <label htmlFor="code" className="block text-sm font-medium text-bark mb-1">Reset code</label>
            <input
              id="code"
              type="text"
              autoComplete="one-time-code"
              autoCapitalize="none"
              autoCorrect="off"
              spellCheck={false}
              required
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="Paste the code from the email"
              className="w-full px-4 py-3 rounded-lg border border-stone bg-cream focus:ring-2 focus:ring-clay focus:outline-none font-mono text-sm"
            />
          </div>
          <div>
            <label htmlFor="new-password" className="block text-sm font-medium text-bark mb-1">New password (at least 12 characters)</label>
            <input
              id="new-password"
              type="password"
              autoComplete="new-password"
              required
              minLength={12}
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="w-full px-4 py-3 rounded-lg border border-stone bg-cream focus:ring-2 focus:ring-clay focus:outline-none"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-clay text-white rounded-lg font-medium hover:bg-bark transition-colors disabled:opacity-50"
          >
            {loading ? "Resetting..." : "Reset Password"}
          </button>
        </form>
      )}

      <p className="text-center text-sm text-dusk mt-6">
        <Link href="/login" className="text-clay underline">Back to login</Link>
      </p>
    </div>
  );
}
