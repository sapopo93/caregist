"use client";

import Link from "next/link";
import type { CSSProperties, ReactNode } from "react";

import { trackEvent } from "@/lib/analytics";

type Props = {
  href: string;
  eventType: string;
  eventSource: string;
  meta?: Record<string, string | number | boolean | null | undefined>;
  className?: string;
  style?: CSSProperties;
  children: ReactNode;
};

export default function TrackedLink({
  href,
  eventType,
  eventSource,
  meta,
  className,
  style,
  children,
}: Props) {
  const handleClick = () => {
    void trackEvent(eventType, eventSource, meta);
  };

  if (href.startsWith("mailto:")) {
    return (
      <a href={href} className={className} style={style} onClick={handleClick}>
        {children}
      </a>
    );
  }

  return (
    <Link href={href} className={className} style={style} onClick={handleClick}>
      {children}
    </Link>
  );
}
