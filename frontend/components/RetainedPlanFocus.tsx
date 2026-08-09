"use client";

import { useEffect } from "react";
import { useSearchParams } from "next/navigation";

import { pricingPlanCardId } from "@/lib/pricing-plan-path";

export default function RetainedPlanFocus() {
  const searchParams = useSearchParams();
  const highlightedPlan = searchParams.get("highlight");

  useEffect(() => {
    const cardId = pricingPlanCardId(highlightedPlan);
    if (!cardId) return;

    const card = document.getElementById(cardId);
    if (!card) return;

    card.scrollIntoView({ behavior: "smooth", block: "center" });
    card.focus({ preventScroll: true });
  }, [highlightedPlan]);

  return null;
}

