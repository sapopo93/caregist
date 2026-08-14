"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { resolvePostVerificationPath } from "@/lib/post-verification";
import { apiErrorMessage } from "@/lib/api-error";

function VerifyEmailScreen() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const email = searchParams.get("email") || "";
  const requestedNext = searchParams.get("next");

  const [resendEmail, setResendEmail] = useState(email);
  const [message, setMessage] = useState(
    token
      ? "Verifying your email..."
      : email
        ? "We sent a verification link to your inbox."
        : "Enter your account email to request a new verification link.",
  );
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [nextPath, setNextPath] = useState("/login");

  useEffect(() => {
    const storedNext = localStorage.getItem("caregist_post_verify_path");
    const safeNext = resolvePostVerificationPath(requestedNext, storedNext);
    setNextPath(safeNext);
    localStorage.setItem("caregist_post_verify_path", safeNext);
  }, [requestedNext]);

  useEffect(() => {
    if (!token) return;
    setStatus("loading");
    fetch("/api/v1/auth/verify-email", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token }),
    })
      .then(async (res) => {
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(apiErrorMessage(data, "Verification failed."));
        const serverNext = resolvePostVerificationPath(
          data.next_path,
          requestedNext,
          localStorage.getItem("caregist_post_verify_path"),
        );
        setNextPath(serverNext);
        localStorage.setItem("caregist_post_verify_path", serverNext);
        setMessage(data.message || "Email verified.");
        setStatus("success");
      })
      .catch((err) => {
        setMessage(err.message || "Verification failed.");
        setStatus("error");
      });
  }, [token]);

  async function handleResend() {
    const targetEmail = resendEmail.trim();
    if (!targetEmail) return;
    setStatus("loading");
    try {
      const res = await fetch("/api/v1/auth/resend-verification", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: targetEmail }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(apiErrorMessage(data, "Verification email could not be sent."));
      setMessage(data.message || "If that email is waiting for verification, a new link has been sent.");
      setStatus("idle");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Verification email could not be sent.");
      setStatus("error");
    }
  }

  return (
    <div className="max-w-md mx-auto px-6 py-16 text-center">
      <h1 className="text-3xl font-bold mb-4">Verify your email</h1>
      <p className="text-dusk mb-6">{message}</p>
      {status === "success" && (
        <button
          onClick={() => {
            localStorage.removeItem("caregist_post_verify_path");
            router.push(nextPath);
          }}
          className="w-full py-3 bg-clay text-white rounded-lg font-medium hover:bg-bark transition-colors mb-3"
        >
          Continue
        </button>
      )}
      {!token && (
        <form
          className="mb-3 space-y-3"
          onSubmit={(event) => {
            event.preventDefault();
            void handleResend();
          }}
        >
          <label htmlFor="verification-email" className="sr-only">Account email</label>
          <input
            id="verification-email"
            type="email"
            autoComplete="email"
            required
            placeholder="your@email.com"
            value={resendEmail}
            onChange={(event) => setResendEmail(event.target.value)}
            className="w-full rounded-lg border border-stone bg-cream px-4 py-3 text-charcoal focus:outline-none focus:ring-2 focus:ring-clay"
          />
          <button
            type="submit"
            disabled={status === "loading" || !resendEmail.trim()}
            className="w-full rounded-lg border border-stone py-3 font-medium text-dusk transition-colors hover:bg-cream disabled:opacity-50"
          >
            {status === "loading" ? "Sending..." : "Resend verification email"}
          </button>
        </form>
      )}
      <Link href={nextPath} className="text-clay underline text-sm">Back to login</Link>
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={<div className="max-w-md mx-auto px-6 py-16 text-center">Loading...</div>}>
      <VerifyEmailScreen />
    </Suspense>
  );
}
