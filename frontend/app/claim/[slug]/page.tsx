"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

interface ClaimFormProps {
  params: { slug: string };
}

interface ClaimResponse {
  data: {
    id: number;
    status: string;
    claimant_name: string;
    claimant_email: string;
  };
  gate: "auto_approved" | "pending_review";
  message: string;
}

export default function ClaimProviderPage({ params }: ClaimFormProps) {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ClaimResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [form, setForm] = useState({
    claimant_name: "",
    claimant_email: "",
    claimant_phone: "",
    claimant_role: "",
    organisation_name: "",
    proof_of_association: "",
    fast_track: false,
  });

  function handleChange(
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) {
    const { name, value, type } = e.target;
    setForm((prev) => ({
      ...prev,
      [name]:
        type === "checkbox" ? (e.target as HTMLInputElement).checked : value,
    }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await fetch(`/api/v1/providers/${params.slug}/claim`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });

      if (!res.ok) {
        const err = await res.json();
        setError(err.detail ?? "Submission failed. Please try again.");
        return;
      }

      const data: ClaimResponse = await res.json();
      setResult(data);
    } catch {
      setError("Network error. Please check your connection and try again.");
    } finally {
      setLoading(false);
    }
  }

  // --- Post-submission result screen ---
  if (result) {
    const isAutoApproved = result.gate === "auto_approved";

    return (
      <main className="max-w-xl mx-auto py-16 px-4">
        <div
          className={`rounded-lg border p-6 ${
            isAutoApproved
              ? "border-green-300 bg-green-50"
              : "border-amber-300 bg-amber-50"
          }`}
        >
          {isAutoApproved ? (
            <>
              <h1 className="text-2xl font-semibold text-green-800 mb-2">
                Claim approved
              </h1>
              <p className="text-green-700">
                Your email domain matched this provider&apos;s registered
                website. Your listing is now active and under your management.
              </p>
              <p className="mt-4 text-sm text-green-600">
                A confirmation has been sent to {result.data.claimant_email}.
              </p>
            </>
          ) : (
            <>
              <h1 className="text-2xl font-semibold text-amber-800 mb-2">
                Claim submitted — pending admin review
              </h1>
              <p className="text-amber-700">
                We couldn&apos;t automatically verify your ownership via domain
                matching. Our team will review your claim within{" "}
                <strong>1–2 business days</strong> and notify you by email.
              </p>
              <p className="mt-4 text-sm text-amber-600">
                Confirmation sent to {result.data.claimant_email}.
              </p>
            </>
          )}

          <button
            onClick={() => router.push("/dashboard")}
            className="mt-6 inline-block rounded-md bg-blue-600 px-5 py-2 text-white text-sm font-medium hover:bg-blue-700"
          >
            Go to dashboard
          </button>
        </div>
      </main>
    );
  }

  // --- Claim submission form ---
  return (
    <main className="max-w-xl mx-auto py-12 px-4">
      <h1 className="text-3xl font-bold mb-2">Claim this provider listing</h1>
      <p className="text-gray-600 mb-8">
        If your email domain matches the provider&apos;s registered website your
        claim will be <strong>automatically approved</strong>. Otherwise it will
        be reviewed by our team within 1–2 business days.
      </p>

      {error && (
        <div className="mb-6 rounded-md border border-red-300 bg-red-50 p-4 text-red-700">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Full name
          </label>
          <input
            name="claimant_name"
            value={form.claimant_name}
            onChange={handleChange}
            required
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Work email address
          </label>
          <input
            name="claimant_email"
            type="email"
            value={form.claimant_email}
            onChange={handleChange}
            required
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
          />
          <p className="mt-1 text-xs text-gray-500">
            Use your organisation email for the best chance of instant approval.
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Phone number (optional)
          </label>
          <input
            name="claimant_phone"
            type="tel"
            value={form.claimant_phone}
            onChange={handleChange}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Your role at this provider
          </label>
          <input
            name="claimant_role"
            value={form.claimant_role}
            onChange={handleChange}
            required
            placeholder="e.g. Registered Manager, Owner, Director"
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Organisation name (optional)
          </label>
          <input
            name="organisation_name"
            value={form.organisation_name}
            onChange={handleChange}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Proof of association
          </label>
          <textarea
            name="proof_of_association"
            value={form.proof_of_association}
            onChange={handleChange}
            required
            rows={4}
            placeholder="Describe your connection to this provider — e.g. CQC registration number, Companies House reference, or other evidence."
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-md bg-blue-600 px-5 py-2.5 text-white font-semibold hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? "Submitting…" : "Submit claim"}
        </button>
      </form>
    </main>
  );
}
