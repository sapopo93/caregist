import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Terms Status | CareGist",
  description: "Controlled pre-launch terms status for CareGist.",
};

export default function TermsPage() {
  return (
    <div className="max-w-3xl mx-auto px-6 py-12">
      <h1 className="text-3xl font-bold mb-2">Terms status</h1>
      <p className="text-dusk text-sm mb-6">Last updated: 30 July 2026</p>

      <div className="rounded-xl border border-amber-400 bg-amber-50 p-4 text-sm text-amber-950 mb-8">
        <strong>Not an offer or operative customer contract.</strong> The operator, contracting
        authority, VAT treatment, customer classification and commercial terms remain subject to
        Human Gate 1 and qualified legal/accounting review. Checkout is disabled by default.
      </div>

      <div className="prose prose-sm text-charcoal space-y-6" style={{ fontFamily: "Lora" }}>
        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">1. Current permitted use</h2>
          <p>
            CareGist currently provides a controlled informational directory of CQC-registered
            services in England. It is not CQC, is not affiliated with or endorsed by CQC, does not
            provide care or professional advice, and does not warrant that source information is
            current or complete. Verify material decisions with the provider and the latest CQC record.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">2. Source rights</h2>
          <p>
            CQC source information is made available under the Open Government Licence v3.0.
            Contains public sector information licensed under the Open Government Licence v3.0.
            CareGist&apos;s software, original presentation and non-CQC enrichment may have separate
            rights; nothing here narrows rights granted directly by the OGL.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">3. Controlled features</h2>
          <p>
            Provider claims, enquiries, reviews, lead intake, exports, paid monitoring, outbound
            webhooks/digests and billing require separately recorded approvals and remain disabled
            or non-delivering by default. A UI description, configured Stripe account, competitor
            price or successful test does not constitute approval or create a right to activation.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">4. No commercial terms yet</h2>
          <p>
            Displayed or historic prices are scenario inputs only. No price, VAT statement,
            subscription start, renewal, cancellation, refund, service level, export licence or
            provider-listing purchase is offered under this controlled draft. Those terms must name
            the verified entity and be approved before checkout is enabled.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">5. Account and acceptable use</h2>
          <p>
            Users must be at least 18, keep credentials confidential, provide accurate information,
            respect technical limits, and not use CareGist to harass, mislead, defame, evade access
            controls, or process personal data unlawfully. Access may be restricted to protect users,
            providers, data subjects or system integrity.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">6. Provider claims and moderation</h2>
          <p>
            A provider claim cannot activate until the claimant&apos;s verified account, identity and
            current authority evidence pass review and a different authorised moderator records the
            decision. Raw evidence documents are not stored in the claim record; only a cryptographic
            fingerprint and structured verification outcome are retained. No current claim is approved
            merely because a request was submitted.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">7. Data freshness</h2>
          <p>
            Source publication time, CareGist ingestion time and reconciliation status are separate.
            CQC gives no warranty and does not guarantee continued supply. CareGist exposes its source
            watermark and freshness state and does not represent a completeness score as care quality.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">8. Governing documents</h2>
          <p>
            Before commercial activation, a qualified reviewer must approve operative terms,
            privacy notices, customer classification, VAT treatment, refunds, liability, complaints,
            data usage and post-termination handling. Until then, this page is a launch-control record,
            not acceptance wording. Questions may be sent to{" "}
            <a href="mailto:legal@caregist.co.uk" className="text-clay underline">legal@caregist.co.uk</a>.
          </p>
        </section>
      </div>
    </div>
  );
}
