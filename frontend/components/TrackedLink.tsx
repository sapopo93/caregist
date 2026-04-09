"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import { trackEvent } from "@/lib/analytics";

type Props = {
  href: string;
  eventType: string;
  eventSource: string;
  meta?: Record<string, string | number | boolean | null | undefined>;
  className?: string;
  children: ReactNode;
};

export default function TrackedLink({
  href,
  eventType,
  eventSource,
  meta,
  className,
  children,
}: Props) {
  const handleClick = () => {
    void trackEvent(eventType, eventSource, meta);
  };

  if (href.startsWith("mailto:")) {
    return (
      <a href={href} className={className} onClick={handleClick}>
        {children}
      </a>
    );
  }

  return (
    <Link href={href} className={className} onClick={handleClick}>
      {children}
    </Link>
  );
}
