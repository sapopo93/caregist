"use client";

import { useEffect, useState } from "react";

const PAID_TIERS = ["starter", "pro", "business", "admin"];

export default function ExportCSVButton({ exportUrl }: { exportUrl: string }) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const tier = localStorage.getItem("caregist_tier");
    if (tier && PAID_TIERS.includes(tier)) {
      setVisible(true);
    }
  }, []);

  if (!visible) return null;

  return (
    <a
      href={exportUrl}
      className="text-sm text-clay underline hover:text-bark"
    >
      Export CSV
    </a>
  );
}
