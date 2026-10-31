"use client";

import { useRef, useState } from "react";
import { DEFAULT_REGION_OPTIONS } from "@/lib/directory-constants";

const RECIPIENT = "outreach@caregist.co.uk";
const SUBJECT = "Weekly Digest request";
const fieldClass = "mt-2 block w-full rounded-lg border border-stone bg-cream px-3 py-3 text-bark focus:outline-none focus:ring-2 focus:ring-clay";

export default function WeeklyDigestEnquiry({ initialRegion }: { initialRegion: string }) {
  const [region, setRegion] = useState(initialRegion);
  const [buyerType, setBuyerType] = useState("");
  const [startDate, setStartDate] = useState("");
  const [copyStatus, setCopyStatus] = useState("");
  const draftRef = useRef<HTMLTextAreaElement>(null);
  const body = `Please review availability for the £150 four-week Weekly Digest pilot. This is an enquiry, not an order.\n\nEngland region: ${region || "[choose a region]"}\nWhat my business sells and which care services interest me: ${buyerType || "[please add]"}\nPreferred start date: ${startDate || "[please add]"}\n\nPlease confirm availability, the agreed scope and the first delivery date before sending any payment request.`;
  const draft = `To: ${RECIPIENT}\nSubject: ${SUBJECT}\n\n${body}`;
  const mailto = `mailto:${RECIPIENT}?subject=${encodeURIComponent(SUBJECT)}&body=${encodeURIComponent(body)}`;

  async function copyDraft() {
    try {
      await navigator.clipboard.writeText(draft);
      setCopyStatus("Copied. Paste the draft into your webmail and send it to outreach@caregist.co.uk. Nothing has been sent yet.");
    } catch {
      draftRef.current?.focus();
      draftRef.current?.select();
      setCopyStatus("Automatic copying is unavailable. The draft is selected below: copy it manually, then paste it into your webmail. Nothing has been sent yet.");
    }
  }

  return (
    <section className="space-y-5 rounded-xl border border-stone bg-parchment p-5 sm:p-8" aria-label="Prepare your Weekly Digest enquiry" onChange={() => setCopyStatus("")}>
      <label className="block text-sm font-medium text-bark" htmlFor="enquiry-region">
        England region
        <select id="enquiry-region" value={region} onChange={(event) => setRegion(event.target.value)} className={fieldClass}>
          <option value="">Choose an England region</option>
          {DEFAULT_REGION_OPTIONS.map((option) => <option key={option} value={option}>{option}</option>)}
        </select>
      </label>
      <label className="block text-sm font-medium text-bark" htmlFor="enquiry-buyer">
        What does your business sell, and which care services interest you? (optional)
        <input id="enquiry-buyer" type="text" maxLength={500} value={buyerType} onChange={(event) => setBuyerType(event.target.value)} className={fieldClass} />
      </label>
      <label className="block text-sm font-medium text-bark" htmlFor="enquiry-start">
        Preferred start date (optional)
        <input id="enquiry-start" type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} className={fieldClass} />
      </label>
      <div>
        <h2 className="text-xl font-bold text-bark">Send from your email</h2>
        <p className="mt-2 text-sm leading-6 text-dusk">Copy the draft below. In Gmail, Outlook or another webmail service, start a new message to <strong>{RECIPIENT}</strong> with the subject <strong>{SUBJECT}</strong>, then paste the enquiry text and send it.</p>
      </div>
      <label htmlFor="enquiry-draft" className="block text-sm font-medium text-bark">
        Your email draft
        <textarea id="enquiry-draft" ref={draftRef} readOnly value={draft} rows={13} className={`${fieldClass} text-sm leading-6`} />
      </label>
      <div className="grid gap-3 sm:grid-cols-2">
        <a
          href={region ? mailto : undefined}
          aria-disabled={!region}
          className={`cta-primary ${region ? "" : "pointer-events-none opacity-50"}`}
          onClick={(event) => { if (!region) event.preventDefault(); }}
        >
          Open in my email app
        </a>
        <button type="button" onClick={() => void copyDraft()} disabled={!region} className="cta-secondary disabled:opacity-50">
          Copy for webmail (Gmail, Outlook.com)
        </button>
      </div>
      <p className="text-xs leading-5 text-dusk">
        Either way, you send the email yourself. Pick the email app option if your computer opens a mail program for email links; pick copy if you use webmail in a browser.
      </p>
      {!region && <p className="text-sm text-dusk">Choose an England region above to prepare your enquiry.</p>}
      <p role="status" className="text-sm leading-6 text-bark">{copyStatus}</p>
      <p className="text-sm leading-6 text-dusk">Nothing is submitted by this page. Your enquiry reaches CareGist only when you send the email. This does not place an order or take payment.</p>
    </section>
  );
}
