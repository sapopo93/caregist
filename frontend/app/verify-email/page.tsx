"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";

function VerifyEmailScreen() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const email = searchParams.get("email") || "";
  const next = searchParams.get("next") || "/login";

  const [message, setMessage] = useState("We sent a verification link to your inbox.");
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");

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
        if (!res.ok) throw new Error(data.detail || "Verification failed.");
        setMessage(data.message || "Email verified.");
        setStatus("success");
      })
      .catch((err) => {
        setMessage(err.message || "Verification failed.");
        setStatus("error");
      });
  }, [token]);

  async function handleResend() {
    if (!email) return;
    setStatus("loading");
    const res = await fetch("/api/v1/auth/resend-verification", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    });
    const data = await res.json().catch(() => ({}));
    setMessage(data.message || "If that email is waiting for verification, a new link has been sent.");
    setStatus("idle");
  }

  return (
    <div className="max-w-md mx-auto px-6 py-16 text-center">
      <h1 className="text-3xl font-bold mb-4">Verify your email</h1>
      <p className="text-dusk mb-6">{message}</p>
      {status === "success" && (
        <button
          onClick={() => router.push(next)}
          className="w-full py-3 bg-clay text-white rounded-lg font-medium hover:bg-bark transition-colors mb-3"
        >
          Continue
        </button>
      )}
      {!token && (
        <button
          onClick={() => void handleResend()}
          disabled={!email}
          className="w-full py-3 border border-stone text-dusk rounded-lg font-medium hover:bg-cream transition-colors disabled:opacity-50 mb-3"
        >
          Resend verification email
        </button>
      )}
      <Link href="/login" className="text-clay underline text-sm">Back to login</Link>
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
