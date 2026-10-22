import type { Metadata } from "next";
import Link from "next/link";
import WeeklyDigestEnquiry from "@/components/WeeklyDigestEnquiry";
import { DEFAULT_REGION_OPTIONS } from "@/lib/directory-constants";

export const metadata: Metadata = {
  title: "Weekly Digest enquiry | CareGist",
  description: "Prepare your enquiry for the £150 four-week Weekly Digest pilot.",
};

export default async function WeeklyDigestEnquiryPage({
  searchParams,
}: {
  searchParams: Promise<{ region?: string | string[] }>;
}) {
  const { region } = await searchParams;
  const initialRegion = typeof region === "string" && DEFAULT_REGION_OPTIONS.includes(region) ? region : "";

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <Link href="/pricing#plan-weekly-digest" className="text-sm text-clay underline">Back to products</Link>
      <h1 className="mb-4 mt-6 text-3xl font-bold text-bark">Enquire about the £150 Weekly Digest pilot</h1>
      <p className="mb-6 leading-7 text-dusk">Four weekly digests for one England region, with no automatic renewal. Prepare your message below, then send it from your own email. CareGist will review availability and confirm the scope and first delivery date before any payment.</p>
      <WeeklyDigestEnquiry key={initialRegion} initialRegion={initialRegion} />
    </main>
  );
}
