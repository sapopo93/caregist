"use client";

import { useState } from "react";
import { submitClaim } from "@/lib/actions";

export default function ClaimModal({ slug, providerName }: { slug: string; providerName: string }) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [role, setRole] = useState("");
  const [orgName, setOrgName] = useState("");
  const [proof, setProof] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; message: string } | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setResult(null);

    const res = await submitClaim(slug, {
      claimant_name: name,
      claimant_email: email,
      claimant_phone: phone || undefined,
      claimant_role: role,
      organisation_name: orgName || undefined,
      proof_of_association: proof,
    });

    setSubmitting(false);
    if (res.error) {
      setResult({ ok: false, message: res.error });
    } else {
      setResult({ ok: true, message: "Claim submitted. We'll review it within 2 business days." });
    }
  }

  if (!open) {
    return (
      <button onClick={() => setOpen(true)}
        className="text-sm text-dusk hover:text-clay underline transition-colors">
        Are you the provider? Claim this listing
      </button>
    );
  }

  if (result?.ok) {
    return (
      <div className="bg-moss/10 border border-moss/30 rounded-lg p-4 text-moss">
        <p className="font-medium">{result.message}</p>
      </div>
    );
  }

  return (
    <div className="border border-stone rounded-lg p-6 bg-cream">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-bold text-bark">Claim {providerName}</h3>
        <button onClick={() => setOpen(false)} className="text-dusk hover:text-charcoal" aria-label="Close">
          <svg className="w-5 h-5" viewBox="0 0 20 20" fill="currentColor"><path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"/></svg>
        </button>
      </div>

      <p className="text-sm text-dusk mb-4">
        Verify your association with this provider to get a Verified badge, respond to reviews, and manage your listing.
      </p>

      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="grid md:grid-cols-2 gap-3">
          <div>
            <label htmlFor="claim-name" className="block text-sm font-medium text-bark mb-1">Your name</label>
            <input id="claim-name" type="text" required maxLength={255} value={name} onChange={(e) => setName(e.target.value)}
              className="w-full border border-stone rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-clay/50" />
          </div>
          <div>
            <label htmlFor="claim-email" className="block text-sm font-medium text-bark mb-1">Work email</label>
            <input id="claim-email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
              className="w-full border border-stone rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-clay/50" />
          </div>
        </div>

        <div className="grid md:grid-cols-2 gap-3">
          <div>
            <label htmlFor="claim-role" className="block text-sm font-medium text-bark mb-1">Role at organisation</label>
            <select id="claim-role" required value={role} onChange={(e) => setRole(e.target.value)}
              className="w-full border border-stone rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-clay/50 bg-white">
              <option value="">Select your role</option>
              <option value="Registered Manager">Registered Manager</option>
              <option value="Owner">Owner / Director</option>
              <option value="Administrator">Administrator</option>
              <option value="Marketing">Marketing / Communications</option>
              <option value="Other">Other</option>
            </select>
          </div>
          <div>
            <label htmlFor="claim-phone" className="block text-sm font-medium text-bark mb-1">Phone <span className="text-dusk font-normal">(optional)</span></label>
            <input id="claim-phone" type="tel" maxLength={20} value={phone} onChange={(e) => setPhone(e.target.value)}
              className="w-full border border-stone rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-clay/50" />
          </div>
        </div>

        <div>
          <label htmlFor="claim-org" className="block text-sm font-medium text-bark mb-1">Organisation name <span className="text-dusk font-normal">(optional)</span></label>
          <input id="claim-org" type="text" maxLength={255} value={orgName} onChange={(e) => setOrgName(e.target.value)}
            className="w-full border border-stone rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-clay/50" />
        </div>

        <div>
          <label htmlFor="claim-proof" className="block text-sm font-medium text-bark mb-1">How are you associated with this provider?</label>
          <textarea id="claim-proof" required maxLength={2000} rows={3} value={proof} onChange={(e) => setProof(e.target.value)}
            placeholder="E.g. I am the registered manager at this location (CQC registration number: ...)"
            className="w-full border border-stone rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-clay/50" />
        </div>

        {result && !result.ok && <p className="text-alert text-sm">{result.message}</p>}

        <div className="flex gap-3">
          <button type="submit" disabled={submitting}
            className="px-5 py-2 bg-clay text-white rounded-lg font-medium hover:bg-bark transition-colors disabled:opacity-50">
            {submitting ? "Submitting..." : "Submit Claim"}
          </button>
          <button type="button" onClick={() => setOpen(false)}
            className="px-5 py-2 border border-stone rounded-lg text-dusk hover:bg-parchment transition-colors">
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
