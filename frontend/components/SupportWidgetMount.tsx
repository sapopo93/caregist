"use client";

import { usePathname } from "next/navigation";

const supportUrl = process.env.NEXT_PUBLIC_SUPPORT_PLATFORM_URL?.replace(/\/$/, "");

export default function SupportWidgetMount() {
  const pathname = usePathname();

  // The pricing page has bottom-right purchase CTAs; avoid floating overlays there.
  if (!supportUrl || pathname === "/pricing") {
    return null;
  }

  return (
    <a
      href={supportUrl}
      target="_blank"
      rel="noopener noreferrer"
      className="fixed bottom-4 right-4 z-40 rounded-full bg-clay px-4 py-3 text-sm font-medium text-white shadow-lg hover:bg-bark transition-colors"
      aria-label="Open CareGist support"
    >
      Support
    </a>
  );
}
