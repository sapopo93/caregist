import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Review Policy | CareGist",
  description: "How CareGist moderates reviews, handles defamation concerns, and ensures fair representation of care providers.",
};

export default function ReviewPolicyPage() {
  return (
    <div className="max-w-3xl mx-auto px-6 py-12">
      <h1 className="text-3xl font-bold mb-2">Review Policy</h1>
      <p className="text-dusk text-sm mb-8">Last updated: 28 March 2026</p>

      <div className="prose prose-sm text-charcoal space-y-6" style={{ fontFamily: "Lora" }}>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">1. Purpose</h2>
          <p>
            CareGist allows users to submit reviews of CQC-registered care providers. Reviews help
            families and professionals make informed care decisions. This policy explains how we moderate
            reviews, what content is acceptable, and how providers and reviewers can raise concerns.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">2. Who can leave a review</h2>
          <p>Reviews should be submitted by people with direct experience of a care provider, including:</p>
          <ul className="list-disc pl-6 space-y-1">
            <li>Current or former residents</li>
            <li>Family members or carers of current or former residents</li>
            <li>Healthcare professionals who have worked with the provider</li>
            <li>People who have received care or services from the provider</li>
          </ul>
          <p className="mt-2">
            We ask reviewers to declare their relationship to the provider (e.g., &quot;family member&quot;,
            &quot;former resident&quot;, &quot;visiting professional&quot;). This is displayed alongside the review.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">3. What we accept</h2>
          <p>Reviews must be:</p>
          <ul className="list-disc pl-6 space-y-1">
            <li><strong>Genuine</strong> — based on real experience with the named provider</li>
            <li><strong>Honest</strong> — an accurate reflection of your experience, whether positive or negative</li>
            <li><strong>Relevant</strong> — about the care, service, or facilities at the provider</li>
            <li><strong>Respectful</strong> — critical opinions are welcome, but personal attacks are not</li>
          </ul>
          <p className="mt-2">
            Both positive and negative reviews are published, provided they meet these criteria.
            We do not filter reviews to favour providers.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">4. What we reject</h2>
          <p>We will not publish reviews that:</p>
          <ul className="list-disc pl-6 space-y-1">
            <li><strong>Are defamatory</strong> — contain false statements of fact that could damage a provider&apos;s reputation. Opinions are protected; false claims of criminal behaviour are not.</li>
            <li><strong>Name individuals</strong> — identify specific staff members, residents, or family members by full name (first names only are acceptable where relevant to the review)</li>
            <li><strong>Contain personal data</strong> — include phone numbers, email addresses, home addresses, or other identifying information of third parties</li>
            <li><strong>Are abusive or threatening</strong> — contain hate speech, threats of violence, or discriminatory language</li>
            <li><strong>Are fake or incentivised</strong> — submitted by the provider about themselves, by competitors to harm a rival, or in exchange for payment or other incentives</li>
            <li><strong>Are off-topic</strong> — not related to the care, service, or facilities at the provider</li>
            <li><strong>Contain spam or advertising</strong> — promote products, services, or other websites</li>
            <li><strong>Relate to ongoing legal proceedings</strong> — could prejudice active court cases or investigations</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">5. Moderation process</h2>
          <p>All reviews are moderated before publication:</p>
          <ol className="list-decimal pl-6 space-y-1">
            <li><strong>Submission</strong> — reviewer submits the review with their name, email, rating (1-5 stars), title, body, and relationship to the provider</li>
            <li><strong>Queue</strong> — the review enters a moderation queue with status &quot;pending&quot;</li>
            <li><strong>Review</strong> — a CareGist moderator reads the review against this policy</li>
            <li><strong>Decision</strong> — the review is either approved (published), edited (see section 8), or rejected (with reason noted internally)</li>
            <li><strong>Publication</strong> — approved reviews are displayed on the provider&apos;s listing page with the reviewer&apos;s display name, rating, relationship, and date</li>
          </ol>
          <p className="mt-2">
            We aim to moderate reviews within 3 working days. During busy periods this may take up to 5
            working days. We do not notify reviewers individually when their review is published.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">6. Moderation discretion</h2>
          <p>
            CareGist reserves the right to approve, reject, edit, or remove any review at our sole
            discretion where we believe it violates this policy, poses legal risk, or cannot be verified
            as a genuine review. We are not obligated to publish any review and are not required to
            provide reasons for rejection.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">7. Evidence of experience</h2>
          <p>
            Where a review contains serious allegations or factual claims, we may request additional
            information from the reviewer to confirm that they have had a genuine experience with the
            provider. This may include approximate dates of care, the type of service received, or
            other verifiable details.
          </p>
          <p className="mt-2">
            If sufficient information cannot be provided within 10 working days of our request, we may
            decline to publish the review.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">8. Editing reviews</h2>
          <p>
            We may edit reviews to remove personal data (such as full names of individuals), defamatory
            statements, or inappropriate language while preserving the overall meaning and opinion
            expressed by the reviewer. Where we make material edits, we will note that the review has
            been edited.
          </p>
          <p className="mt-2">
            We will not change the rating (star score) or alter the substance of a reviewer&apos;s opinion.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">9. Defamation and legal concerns</h2>
          <p>
            We take defamation seriously. Under the Defamation Act 2013 (England and Wales), CareGist
            benefits from the defence available to operators of websites under Section 5, provided we
            respond appropriately to complaints about defamatory content.
          </p>

          <h3 className="text-lg font-semibold text-bark mt-4 mb-2">9.1 If you are a care provider</h3>
          <p>If you believe a review is defamatory or factually inaccurate:</p>
          <ol className="list-decimal pl-6 space-y-1">
            <li>Email <a href="mailto:reviews@caregist.co.uk" className="text-clay underline">reviews@caregist.co.uk</a> with the provider name, the review in question, and a clear explanation of which statements you believe are false and why</li>
            <li>We will review your complaint within 5 working days</li>
            <li>If the review contains statements of fact that appear to be false, we will remove or edit the review</li>
            <li>If the review expresses a genuinely held opinion, we may leave it published but offer you the opportunity to post a public response</li>
            <li>In cases of serious defamation, we will cooperate with legal proceedings and may disclose the reviewer&apos;s email address under court order</li>
          </ol>

          <h3 className="text-lg font-semibold text-bark mt-4 mb-2">9.2 If you are a reviewer</h3>
          <p>
            You are legally responsible for the content of your review. Expressing a genuine opinion
            based on real experience is protected. Making false statements of fact that damage a
            provider&apos;s reputation may expose you to a defamation claim. If in doubt, focus on
            describing your experience rather than making allegations.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">10. Provider responses</h2>
          <p>
            Care providers who have claimed their listing on CareGist may submit a public response
            to any review. Provider responses are subject to the same moderation standards as reviews.
            Responses must be professional, factual, and must not identify residents or disclose
            confidential information.
          </p>
          <p className="mt-2">
            Where possible, we will notify a provider when a new review is published about them and
            offer them the opportunity to respond. Provider responses are usually published within
            3 working days of submission.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">11. Removal requests</h2>
          <ul className="list-disc pl-6 space-y-1">
            <li><strong>Reviewers</strong> may request removal of their own review at any time by emailing <a href="mailto:reviews@caregist.co.uk" className="text-clay underline">reviews@caregist.co.uk</a></li>
            <li><strong>Providers</strong> may request removal of a review they believe violates this policy, following the process in section 9.1</li>
            <li><strong>Third parties</strong> named in a review may request removal of their personal data under UK GDPR Article 17 (right to erasure)</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">12. Responsibility for reviews</h2>
          <p>
            Reviews are the opinions of individual users and do not represent the views of CareGist.
            CareGist does not endorse and is not responsible for the content, accuracy, or completeness
            of user reviews. Users are solely responsible for the content they submit.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">13. Reviewer identity</h2>
          <p>
            Reviews are displayed using the name provided by the reviewer. Reviewers may use their
            first name only if they prefer. We do not publish email addresses. Your email is used
            only for moderation correspondence and will not be shared publicly unless required by
            court order.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">14. Aggregate ratings</h2>
          <p>
            Provider listings display an average star rating calculated from all approved reviews.
            This is separate from the CQC inspection rating. We clearly label these as
            &quot;User reviews&quot; to distinguish them from official CQC ratings.
          </p>
          <p className="mt-2">
            A minimum of 1 approved review is required before an average rating is displayed.
            We do not weight, filter, or algorithmically adjust review scores.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">15. Safeguarding</h2>
          <p>
            If a review raises safeguarding concerns about a care provider (e.g., allegations of abuse,
            neglect, or unsafe conditions), we will:
          </p>
          <ul className="list-disc pl-6 space-y-1">
            <li>Not publish the review until we have assessed the content</li>
            <li>Direct the reviewer to report their concerns directly to CQC (03000 616161 or <a href="https://www.cqc.org.uk/give-feedback-on-care" className="text-clay underline" target="_blank" rel="noopener noreferrer">cqc.org.uk/give-feedback-on-care</a>) and, if appropriate, to the local authority safeguarding team</li>
            <li>Consider whether the review content is appropriate for publication after the reviewer has reported to the relevant authorities</li>
          </ul>
          <p className="mt-2">
            CareGist is a directory service. We are not a regulatory body and cannot investigate
            allegations of poor care. If someone is in immediate danger, call 999.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">16. Contact</h2>
          <p>
            For questions about reviews, moderation, or to report a concern:{" "}
            <a href="mailto:reviews@caregist.co.uk" className="text-clay underline">reviews@caregist.co.uk</a>
          </p>
        </section>

      </div>
    </div>
  );
}
