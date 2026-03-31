"use client";

import { useState } from "react";

export default function ApiApplicationForm() {
  const [form, setForm] = useState({
    company_name: "",
    contact_name: "",
    contact_email: "",
    use_case: "",
    expected_volume: "<10k",
  });
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [errorMsg, setErrorMsg] = useState("");

  function update(field: string, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setStatus("loading");
    setErrorMsg("");

    try {
      const res = await fetch("/api/v1/api-applications", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Submission failed");
      }
      setStatus("success");
    } catch (err: any) {
      setErrorMsg(err.message || "Something went wrong.");
      setStatus("error");
    }
  }

  if (status === "success") {
    return (
      <div className="bg-moss/10 border border-moss/30 rounded-lg p-8 text-center">
        <p className="text-moss font-semibold text-lg">Application received!</p>
        <p className="text-dusk mt-2">We&apos;ll review your application within 2 business days and be in touch.</p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-bark mb-1">Company</label>
          <input
            type="text"
            required
            value={form.company_name}
            onChange={(e) => update("company_name", e.target.value)}
            className="w-full px-4 py-2.5 rounded-lg border border-stone bg-white text-sm"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-bark mb-1">Your name</label>
          <input
            type="text"
            required
            value={form.contact_name}
            onChange={(e) => update("contact_name", e.target.value)}
            className="w-full px-4 py-2.5 rounded-lg border border-stone bg-white text-sm"
          />
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-bark mb-1">Email</label>
          <input
            type="email"
            required
            value={form.contact_email}
            onChange={(e) => update("contact_email", e.target.value)}
            className="w-full px-4 py-2.5 rounded-lg border border-stone bg-white text-sm"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-bark mb-1">Expected monthly requests</label>
          <select
            value={form.expected_volume}
            onChange={(e) => update("expected_volume", e.target.value)}
            className="w-full px-4 py-2.5 rounded-lg border border-stone bg-white text-sm"
          >
            <option value="<10k">&lt;10,000</option>
            <option value="10k-100k">10,000 – 100,000</option>
            <option value="100k-1M">100,000 – 1,000,000</option>
            <option value="1M+">1,000,000+</option>
          </select>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-bark mb-1">Use case</label>
        <textarea
          required
          rows={4}
          placeholder="Describe how you plan to use CareGist data..."
          value={form.use_case}
          onChange={(e) => update("use_case", e.target.value)}
          className="w-full px-4 py-2.5 rounded-lg border border-stone bg-white text-sm"
        />
      </div>

      {status === "error" && (
        <p className="text-alert text-sm">{errorMsg}</p>
      )}

      <button
        type="submit"
        disabled={status === "loading"}
        className="w-full py-3 bg-clay text-white rounded-lg font-medium hover:bg-bark transition-colors disabled:opacity-50"
      >
        {status === "loading" ? "Submitting..." : "Apply for API Access"}
      </button>
    </form>
  );
}
