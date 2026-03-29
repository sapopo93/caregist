"use client";

import { useState } from "react";
import { submitEnquiry } from "@/lib/actions";

export default function EnquiryForm({ slug, providerName }: { slug: string; providerName: string }) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [relationship, setRelationship] = useState("");
  const [careType, setCareType] = useState("");
  const [urgency, setUrgency] = useState("exploring");
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; message: string } | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setResult(null);

    const res = await submitEnquiry(slug, {
      enquirer_name: name,
      enquirer_email: email,
      enquirer_phone: phone || undefined,
      relationship: relationship || undefined,
      care_type: careType || undefined,
      urgency,
      message,
    });

    setSubmitting(false);
    if (res.error) {
      setResult({ ok: false, message: res.error });
    } else {
      setResult({ ok: true, message: "Your enquiry has been sent. The provider will be in touch soon." });
      setName("");
      setEmail("");
      setPhone("");
      setRelationship("");
      setCareType("");
      setUrgency("exploring");
      setMessage("");
    }
  }

  if (result?.ok) {
    return (
      <div className="bg-cream border border-stone rounded-lg p-6">
        <div className="bg-moss/10 border border-moss/30 rounded-lg p-4 text-moss text-center">
          <svg className="w-8 h-8 mx-auto mb-2" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z" clipRule="evenodd" />
          </svg>
          <p className="font-medium text-lg">{result.message}</p>
          <p className="text-sm mt-1 opacity-80">Your details will only be shared with {providerName}.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-cream border-2 border-clay/30 rounded-lg p-6 mb-6">
      <h2 className="text-xl font-bold mb-1">Enquire about {providerName}</h2>
      <p className="text-sm text-dusk mb-4">Your details will only be shared with this provider.</p>

      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="grid md:grid-cols-2 gap-3">
          <div>
            <label htmlFor="enq-name" className="block text-sm font-medium text-bark mb-1">Your name</label>
            <input id="enq-name" type="text" required maxLength={255} value={name} onChange={(e) => setName(e.target.value)}
              className="w-full border border-stone rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-clay/50" />
          </div>
          <div>
            <label htmlFor="enq-email" className="block text-sm font-medium text-bark mb-1">Email</label>
            <input id="enq-email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
              className="w-full border border-stone rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-clay/50" />
          </div>
        </div>

        <div className="grid md:grid-cols-3 gap-3">
          <div>
            <label htmlFor="enq-phone" className="block text-sm font-medium text-bark mb-1">Phone <span className="text-dusk font-normal">(optional)</span></label>
            <input id="enq-phone" type="tel" maxLength={20} value={phone} onChange={(e) => setPhone(e.target.value)}
              className="w-full border border-stone rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-clay/50" />
          </div>
          <div>
            <label htmlFor="enq-relationship" className="block text-sm font-medium text-bark mb-1">I am a</label>
            <select id="enq-relationship" value={relationship} onChange={(e) => setRelationship(e.target.value)}
              className="w-full border border-stone rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-clay/50 bg-white">
              <option value="">Select (optional)</option>
              <option value="family_member">Family member</option>
              <option value="self">Looking for myself</option>
              <option value="professional">Healthcare professional</option>
              <option value="friend">Friend</option>
              <option value="other">Other</option>
            </select>
          </div>
          <div>
            <label htmlFor="enq-urgency" className="block text-sm font-medium text-bark mb-1">Timeframe</label>
            <select id="enq-urgency" value={urgency} onChange={(e) => setUrgency(e.target.value)}
              className="w-full border border-stone rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-clay/50 bg-white">
              <option value="exploring">Just exploring</option>
              <option value="within_month">Need within a month</option>
              <option value="urgent">Urgent</option>
            </select>
          </div>
        </div>

        <div>
          <label htmlFor="enq-care" className="block text-sm font-medium text-bark mb-1">Type of care needed <span className="text-dusk font-normal">(optional)</span></label>
          <input id="enq-care" type="text" maxLength={100} value={careType} onChange={(e) => setCareType(e.target.value)}
            placeholder="E.g. Residential, Nursing, Dementia, Home care"
            className="w-full border border-stone rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-clay/50" />
        </div>

        <div>
          <label htmlFor="enq-message" className="block text-sm font-medium text-bark mb-1">Your message</label>
          <textarea id="enq-message" required maxLength={5000} rows={4} value={message} onChange={(e) => setMessage(e.target.value)}
            placeholder="Tell the provider about your situation and what you're looking for..."
            className="w-full border border-stone rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-clay/50" />
        </div>

        {result && !result.ok && <p className="text-alert text-sm">{result.message}</p>}

        <button type="submit" disabled={submitting}
          className="w-full px-6 py-3 bg-clay text-white rounded-lg font-medium text-lg hover:bg-bark transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
          {submitting ? "Sending..." : "Send Enquiry"}
        </button>
      </form>
    </div>
  );
}
