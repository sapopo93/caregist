"use client";

const supportUrl = process.env.NEXT_PUBLIC_SUPPORT_PLATFORM_URL;
const supportToken = process.env.NEXT_PUBLIC_SUPPORT_PLATFORM_TOKEN;

export default function SupportWidgetMount() {
  if (!supportUrl || !supportToken) {
    return null;
  }

  return (
    <a
      href="mailto:hello@caregist.co.uk"
      className="fixed bottom-4 right-4 z-40 rounded-full bg-clay px-4 py-3 text-sm font-medium text-white shadow-lg hover:bg-bark transition-colors"
      aria-label="Contact CareGist support"
    >
      Contact support
    </a>
  );
}
