import Link from "next/link";

export const metadata = { title: "Territory Brief order | CareGist", robots: { index: false } };
export const dynamic = "force-dynamic";

export default function TerritoryBriefSuccessPage() {
  return (
    <main className="mx-auto max-w-2xl px-6 py-16">
      <h1 className="text-3xl font-semibold">Check your email for your Territory Brief</h1>
      <p className="mt-6">After Stripe confirms payment and your brief is prepared, we will email your private PDF and CSV download links to the address you used at checkout.</p>
      <p className="mt-4">This page does not confirm payment or delivery. If your links do not arrive, contact <a href="mailto:support@caregist.co.uk">support@caregist.co.uk</a> with your Stripe receipt reference. Do not pay again.</p>
      <p className="mt-6"><Link href="/territory-opportunity-brief">Return to the Territory Opportunity Brief</Link></p>
    </main>
  );
}
