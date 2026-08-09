import type { Metadata } from "next";

import ApiApplicationForm from "@/components/ApiApplicationForm";
import { CQC_INDEPENDENCE_LINE } from "@/lib/caregist-config";

export const metadata: Metadata = {
  title: "CareGist Intelligence Feed | CQC Signal Integration",
  description:
    "A sales-assisted pilot for integrating verified CQC new-registration or rating-change events through an API and signed webhooks.",
};

const EVENT_EXAMPLE = `{
  "schema_version": "1.0",
  "event_id": "evt_...",
  "event_type": "rating_changed",
  "entity": {
    "level": "location",
    "cqc_location_id": "1-123456789",
    "name": "Example Care Service"
  },
  "change": { "old": "Good", "new": "Requires improvement" },
  "source_checked_at": "2026-08-09T10:30:00Z",
  "source": {
    "url": "https://www.cqc.org.uk/location/1-123456789",
    "licence": "OGL-3.0",
    "snapshot_sha256": "..."
  },
  "explanation": { "status": "unavailable" }
}`;

export default function IntelligenceFeedPage() {
  return (
    <main className="mx-auto max-w-5xl px-6 py-16">
      <header className="mb-12 max-w-3xl">
        <p className="mb-3 font-mono text-xs uppercase tracking-[0.22em] text-clay">
          Sales-assisted · from £6,000/year
        </p>
        <h1 className="mb-5 text-4xl font-extrabold text-bark">
          Put verified CQC changes into the system your team already uses
        </h1>
        <p className="text-lg leading-8 text-dusk" style={{ fontFamily: "Lora" }}>
          The Intelligence Feed Pilot delivers one agreed signal in one England
          region through a canonical API and timestamp-signed webhooks. It is an
          integration product—not a static dataset download.
        </p>
      </header>

      <section className="mb-12 grid gap-5 md:grid-cols-3">
        {[
          {
            title: "Traceable by default",
            body: "Stable CQC IDs, source URL, observation times, and a snapshot checksum travel with every event.",
          },
          {
            title: "Safe delivery",
            body: "Stable cursors, timestamped HMAC signatures, replay, idempotency, bounded retry, and delivery health.",
          },
          {
            title: "Narrow on purpose",
            body: "The base pilot covers one region and either new registrations or rating changes, with limitations written into scope.",
          },
        ].map((item) => (
          <article key={item.title} className="rounded-xl border border-stone bg-cream p-5">
            <h2 className="mb-2 font-bold text-bark">{item.title}</h2>
            <p className="text-sm leading-6 text-dusk">{item.body}</p>
          </article>
        ))}
      </section>

      <section className="mb-12 grid gap-8 md:grid-cols-2 md:items-start">
        <div>
          <h2 className="mb-3 text-2xl font-bold text-bark">A canonical event, not a mutable row</h2>
          <p className="mb-5 text-sm leading-6 text-dusk">
            Consumers receive a stable event identifier and the original entity level.
            A location-level change is never promoted into an unsupported provider-group conclusion.
          </p>
          <ul className="space-y-2 text-sm text-charcoal">
            <li>✓ New registrations and rating changes only at launch</li>
            <li>✓ Direct official-source links and evidence metadata</li>
            <li>✓ Explanation omitted if evidence validation fails</li>
            <li>✓ No predictive score, vacancy claim, or speculative opportunity label</li>
          </ul>
        </div>
        <pre className="overflow-x-auto rounded-xl bg-charcoal p-5 font-mono text-xs leading-5 text-cream">
          {EVENT_EXAMPLE}
        </pre>
      </section>

      <section className="rounded-xl border border-stone bg-parchment p-6">
        <h2 className="mb-2 text-2xl font-bold text-bark">Scope an Intelligence Feed pilot</h2>
        <p className="mb-6 text-sm leading-6 text-dusk">
          Tell us the region, signal, receiving system, and operational decision. We
          qualify the use case before any quote, invoice, or production delivery.
        </p>
        <ApiApplicationForm />
      </section>

      <footer className="mt-8 text-center text-xs text-dusk">
        CQC information is reused under the Open Government Licence v3.0. {CQC_INDEPENDENCE_LINE}
      </footer>
    </main>
  );
}
