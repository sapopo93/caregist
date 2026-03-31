"use client";

import { useState } from "react";
import { submitClaim } from "@/lib/actions";

const ROLES = ["Registered Manager", "Nominated Individual", "Provider Director", "Other"];

export default function ClaimStepper({
  slug,
  providerName,
  providerId,
}: {
  slug: string;
  providerName: string;
  providerId?: string;
}) {
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Step 1 fields
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [role, setRole] = useState(ROLES[0]);

  // Step 2 fields
  const [proof, setProof] = useState(providerId || slug);
  const [fastTrack, setFastTrack] = useState(false);

  async function handleSubmit() {
    setLoading(true);
    setError("");
    const res = await submitClaim(slug, {
      claimant_name: name,
      claimant_email: email,
      claimant_phone: phone || undefined,
      claimant_role: role,
      proof_of_association: proof,
      fast_track: fastTrack,
    });
    setLoading(false);
    if (res.error) {
      setError(res.error);
    } else {
      setStep(3);
    }
  }

  return (
    <div>
      {/* Progress */}
      <div className="flex items-center gap-2 mb-8">
        {[1, 2, 3].map((s) => (
          <div key={s} className="flex items-center gap-2">
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                step >= s ? "bg-clay text-white" : "bg-stone text-dusk"
              }`}
            >
              {s}
            </div>
            {s < 3 && <div className={`w-8 h-0.5 ${step > s ? "bg-clay" : "bg-stone"}`} />}
          </div>
        ))}
        <span className="text-xs text-dusk ml-2">
          {step === 1 ? "Identify" : step === 2 ? "Verify" : "Pending"}
        </span>
      </div>

      {step === 1 && (
        <div className="space-y-4">
          <h2 className="text-xl font-bold text-bark">Claim {providerName}</h2>
          <p className="text-sm text-dusk">Tell us about your role at this provider.</p>

          <div>
            <label className="block text-sm font-medium text-bark mb-1">Your role</label>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="w-full px-4 py-2.5 rounded-lg border border-stone bg-white text-sm"
            >
              {ROLES.map((r) => (
                <option key={r} value={r}>{r}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-bark mb-1">Your name</label>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-4 py-2.5 rounded-lg border border-stone bg-white text-sm"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-bark mb-1">Work email</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-4 py-2.5 rounded-lg border border-stone bg-white text-sm"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-bark mb-1">Phone (optional)</label>
            <input
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              className="w-full px-4 py-2.5 rounded-lg border border-stone bg-white text-sm"
            />
          </div>

          <button
            onClick={() => {
              if (!name.trim() || !email.trim()) return;
              setStep(2);
            }}
            className="w-full py-3 bg-clay text-white rounded-lg font-medium hover:bg-bark transition-colors"
          >
            Next
          </button>
        </div>
      )}

      {step === 2 && (
        <div className="space-y-4">
          <h2 className="text-xl font-bold text-bark">Verify your connection</h2>
          <p className="text-sm text-dusk">
            We&apos;ll verify your claim against the CQC register. Enter the CQC location ID
            or describe your proof of association.
          </p>

          <div>
            <label className="block text-sm font-medium text-bark mb-1">
              CQC location ID or proof of association
            </label>
            <textarea
              rows={3}
              value={proof}
              onChange={(e) => setProof(e.target.value)}
              className="w-full px-4 py-2.5 rounded-lg border border-stone bg-white text-sm"
            />
          </div>

          <label className="flex items-center gap-2 text-sm text-dusk">
            <input
              type="checkbox"
              checked={fastTrack}
              onChange={(e) => setFastTrack(e.target.checked)}
              className="rounded"
            />
            Fast-track review (24 hours instead of 48)
          </label>

          {error && (
            <div className="text-alert text-sm bg-alert/10 border border-alert/30 rounded-lg p-3">
              {error}
            </div>
          )}

          <div className="flex gap-3">
            <button
              onClick={() => setStep(1)}
              className="flex-1 py-3 border border-stone text-dusk rounded-lg font-medium hover:bg-parchment transition-colors"
            >
              Back
            </button>
            <button
              onClick={handleSubmit}
              disabled={loading || !proof.trim()}
              className="flex-1 py-3 bg-clay text-white rounded-lg font-medium hover:bg-bark transition-colors disabled:opacity-50"
            >
              {loading ? "Submitting..." : "Submit Claim"}
            </button>
          </div>
        </div>
      )}

      {step === 3 && (
        <div className="text-center py-8">
          <div className="w-16 h-16 rounded-full bg-moss/15 flex items-center justify-center mx-auto mb-4">
            <span className="text-moss text-2xl">&#10003;</span>
          </div>
          <h2 className="text-xl font-bold text-bark mb-2">Claim submitted</h2>
          <p className="text-dusk mb-4">
            We&apos;ll review your claim within {fastTrack ? "24 hours" : "24\u201348 hours"} and send
            a verification email to the registered address on file with CQC.
          </p>
          {!fastTrack && (
            <p className="text-sm text-dusk">
              Need it faster?{" "}
              <span className="text-clay font-medium">
                Fast-track for \u00A349 — reviewed within 24 hours.
              </span>
            </p>
          )}
          <a
            href={`/provider/${slug}`}
            className="inline-block mt-6 px-6 py-3 bg-clay text-white rounded-lg font-medium hover:bg-bark transition-colors"
          >
            Back to provider
          </a>
        </div>
      )}
    </div>
  );
}
