"use client";

import { useEffect, useState } from "react";

const DIMENSION_LABELS: Record<string, string> = {
  rating_safe: "Safe",
  rating_effective: "Effective",
  rating_caring: "Caring",
  rating_responsive: "Responsive",
  rating_well_led: "Well-led",
};

const RATING_SCORE: Record<string, number> = {
  Outstanding: 100,
  Good: 75,
  "Requires Improvement": 40,
  Inadequate: 15,
};

const RATING_COLOR: Record<string, string> = {
  Outstanding: "#4A5E45",
  Good: "#D4943A",
  "Requires Improvement": "#C44444",
  Inadequate: "#8B0000",
};

const NATIONAL_AVG_QUALITY = 74;

const VISIT_QUESTIONS: Record<string, string[]> = {
  rating_safe: [
    "How do you manage medication — who administers it and how are errors tracked?",
    "What is your staffing ratio during the day and at night?",
    "How do you handle falls prevention and what equipment do you have?",
  ],
  rating_effective: [
    "How do you create and review individual care plans?",
    "What training do your staff receive and how often?",
    "How do you work with GPs, hospitals, and other health professionals?",
  ],
  rating_caring: [
    "Can I see how you involve residents in decisions about their care?",
    "How do you support residents to maintain their dignity and independence?",
    "What activities and social opportunities do you offer?",
  ],
  rating_responsive: [
    "How do you handle complaints and how quickly are they resolved?",
    "How do you adapt care when someone's needs change?",
    "Can residents choose their daily routine — when to eat, sleep, go out?",
  ],
  rating_well_led: [
    "How long has the registered manager been here?",
    "How do you gather feedback from residents and families?",
    "What quality audits do you carry out and what did the last one find?",
  ],
};

interface Props {
  provider: any;
}

export default function CareGistAssessment({ provider }: Props) {
  const [nearbyData, setNearbyData] = useState<{ rank: number; total: number; topAlternative: any } | null>(null);

  const qualityScore = provider.quality_score;
  const hasRatings = provider.overall_rating && provider.overall_rating !== "Not Yet Inspected";

  useEffect(() => {
    if (provider.latitude && provider.longitude) {
      fetch(`/api/v1/providers/nearby/search?lat=${provider.latitude}&lon=${provider.longitude}&radius_km=8&per_page=50`)
        .then((r) => r.ok ? r.json() : null)
        .then((data) => {
          if (!data?.data) return;
          const nearby = data.data.filter((p: any) => p.id !== provider.id && p.quality_score);
          const allWithSelf = [...nearby, { ...provider, quality_score: qualityScore }]
            .sort((a: any, b: any) => (b.quality_score || 0) - (a.quality_score || 0));
          const rank = allWithSelf.findIndex((p: any) => p.id === provider.id) + 1;
          const topAlt = nearby.find((p: any) => p.id !== provider.id && p.quality_score > (qualityScore || 0));
          setNearbyData({ rank, total: allWithSelf.length, topAlternative: topAlt || null });
        })
        .catch(() => {});
    }
  }, [provider.latitude, provider.longitude, provider.id, qualityScore]);

  if (!hasRatings && !qualityScore) return null;

  // Data Confidence Index — degrades as inspection ages
  const dataConfidence = (() => {
    if (!provider.last_inspection_date) return 10;
    const days = Math.floor((Date.now() - new Date(provider.last_inspection_date).getTime()) / 86400000);
    return Math.max(10, Math.round(100 - (days / 14)));
  })();
  const confidenceColor = dataConfidence >= 70 ? "#4A5E45" : dataConfidence >= 40 ? "#D4943A" : "#C44444";
  const confidenceLabel = dataConfidence >= 70 ? "High" : dataConfidence >= 40 ? "Moderate" : "Low";

  // Determine trajectory from rating history if available
  const trajectory = provider.inspection_summary?.includes("improved") ? "improving"
    : provider.inspection_summary?.includes("downgraded") ? "declining"
    : "stable";

  // All 5 dimensions — including unassessed ones
  const allDimensions = Object.entries(DIMENSION_LABELS)
    .map(([key, label]) => ({
      key,
      label,
      rating: provider[key] || null,
      score: RATING_SCORE[provider[key]] || 0,
      assessed: !!provider[key],
    }));
  const dimensions = allDimensions.filter((d) => d.assessed);
  const unassessedCount = allDimensions.filter((d) => !d.assessed).length;

  const weakest = dimensions.length > 0 ? dimensions.reduce((a, b) => a.score < b.score ? a : b) : null;
  const strongest = dimensions.length > 0 ? dimensions.reduce((a, b) => a.score > b.score ? a : b) : null;

  // Generate visit questions from weakest dimensions
  const questions: string[] = [];
  const weakDims = dimensions.filter((d) => d.score <= 40);
  if (weakDims.length > 0) {
    for (const d of weakDims.slice(0, 2)) {
      const qs = VISIT_QUESTIONS[d.key];
      if (qs) questions.push(qs[0]);
    }
  }
  if (questions.length === 0 && weakest) {
    const qs = VISIT_QUESTIONS[weakest.key];
    if (qs) questions.push(qs[0]);
  }
  // Always add a general question
  questions.push("Can I visit at different times of day to see the home in its normal routine?");

  const aboveAvg = qualityScore && qualityScore > NATIONAL_AVG_QUALITY;

  return (
    <div className="bg-white border-2 border-clay/30 rounded-xl p-6 mb-6 print:border print:border-stone" id="assessment">
      {/* Header */}
      <div className="flex items-center gap-3 mb-5">
        <div className="w-10 h-10 bg-clay rounded-lg flex items-center justify-center text-white font-bold text-lg">C</div>
        <div>
          <h2 className="text-xl font-bold text-bark">CareGist Assessment</h2>
          <p className="text-xs text-dusk">Independent analysis based on CQC inspection data</p>
        </div>
      </div>

      {/* Quality Verdict */}
      {qualityScore && (
        <div className="bg-parchment rounded-lg p-5 mb-4">
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-semibold text-bark">Quality Score</span>
            <span className="text-2xl font-bold" style={{ color: qualityScore >= 80 ? "#4A5E45" : qualityScore >= 60 ? "#D4943A" : "#C44444" }}>
              {qualityScore}<span className="text-sm text-dusk font-normal">/100</span>
            </span>
          </div>
          <div className="w-full bg-stone/30 rounded-full h-3 mb-2">
            <div
              className="h-3 rounded-full transition-all"
              style={{
                width: `${qualityScore}%`,
                backgroundColor: qualityScore >= 80 ? "#4A5E45" : qualityScore >= 60 ? "#D4943A" : "#C44444",
              }}
            />
          </div>
          <div className="flex justify-between text-xs text-dusk">
            <span>National average: {NATIONAL_AVG_QUALITY}/100</span>
            <span className={aboveAvg ? "text-moss font-semibold" : "text-alert font-semibold"}>
              {aboveAvg ? "Above average" : "Below average"}
            </span>
          </div>
        </div>
      )}

      {/* Data Confidence */}
      <div className="bg-parchment rounded-lg p-4 mb-4">
        <div className="flex items-center justify-between mb-2">
          <div>
            <span className="text-sm font-semibold text-bark">Data Confidence</span>
          </div>
          <div className="text-right">
            <span className="text-xl font-bold" style={{ color: confidenceColor }}>{dataConfidence}%</span>
            <span className="text-xs font-semibold ml-1" style={{ color: confidenceColor }}>{confidenceLabel}</span>
          </div>
        </div>
        <div className="w-full bg-stone/30 rounded-full h-2.5 mb-2">
          <div
            className="h-2.5 rounded-full transition-all"
            style={{ width: `${dataConfidence}%`, backgroundColor: confidenceColor }}
          />
        </div>
        {provider.last_inspection_date && (
          <p className="text-xs" style={{ color: confidenceColor }}>
            {(() => {
              const dateStr = new Date(provider.last_inspection_date).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" });
              if (dataConfidence >= 70) return `Last inspected ${dateStr} — ratings from this period are highly reliable.`;
              if (dataConfidence >= 40) return `Last inspected ${dateStr} — ratings from this period are moderately reliable.`;
              return `Last inspected ${dateStr} — this inspection is over 2 years old. Consider contacting the provider for current information.`;
            })()}
          </p>
        )}
        <p className="text-[10px] text-dusk mt-1">Data confidence reflects inspection recency, not the quality of care provided.</p>
      </div>

      {/* Local Rank */}
      {nearbyData && (
        <div className="bg-parchment rounded-lg p-4 mb-4 flex items-center justify-between">
          <div>
            <span className="text-sm font-semibold text-bark">Local Rank</span>
            <p className="text-xs text-dusk mt-0.5">Within 5 miles of {provider.postcode}</p>
          </div>
          <div className="text-right">
            <span className="text-2xl font-bold text-clay">#{nearbyData.rank}</span>
            <span className="text-sm text-dusk"> of {nearbyData.total}</span>
          </div>
        </div>
      )}

      {/* Dimension Breakdown */}
      {hasRatings && (
        <div className="mb-4">
          <p className="text-sm font-semibold text-bark mb-3">CQC Dimension Analysis</p>
          <div className="space-y-2">
            {allDimensions.map((d) => {
              if (!d.assessed) {
                return (
                  <div key={d.key} className="flex items-center gap-3 opacity-50">
                    <span className="text-xs text-dusk w-20 shrink-0">{d.label}</span>
                    <div className="flex-1 bg-stone/10 rounded-full h-2.5" />
                    <span className="text-xs text-dusk px-2 py-0.5 rounded-full shrink-0 bg-stone/10">
                      Not assessed
                    </span>
                  </div>
                );
              }
              const color = RATING_COLOR[d.rating] || "#8a6a4a";
              return (
                <div key={d.key} className="flex items-center gap-3">
                  <span className="text-xs text-dusk w-20 shrink-0">{d.label}</span>
                  <div className="flex-1 bg-stone/20 rounded-full h-2.5">
                    <div
                      className="h-2.5 rounded-full"
                      style={{ width: `${d.score}%`, backgroundColor: color }}
                    />
                  </div>
                  <span
                    className="text-xs font-semibold px-2 py-0.5 rounded-full shrink-0"
                    style={{ backgroundColor: color + "15", color }}
                  >
                    {d.rating}
                  </span>
                </div>
              );
            })}
          </div>
          {unassessedCount > 0 && (
            <p className="text-xs text-dusk mt-2">
              {unassessedCount} dimension{unassessedCount > 1 ? "s were" : " was"} not evaluated in the most recent inspection.
            </p>
          )}
        </div>
      )}

      {/* Flags */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        {/* Green flags */}
        <div className="bg-moss/5 rounded-lg p-3">
          <p className="text-xs font-bold text-moss mb-2">Strengths</p>
          <ul className="space-y-1">
            {strongest && strongest.rating === "Outstanding" && (
              <li className="text-xs text-charcoal">Outstanding in {strongest.label}</li>
            )}
            {aboveAvg && <li className="text-xs text-charcoal">Above national average quality</li>}
            {nearbyData && nearbyData.rank <= 3 && (
              <li className="text-xs text-charcoal">Top 3 locally</li>
            )}
            {provider.number_of_beds > 0 && (
              <li className="text-xs text-charcoal">{provider.number_of_beds} beds</li>
            )}
          </ul>
        </div>
        {/* Red flags */}
        <div className="bg-alert/5 rounded-lg p-3">
          <p className="text-xs font-bold text-alert mb-2">Watch Points</p>
          <ul className="space-y-1">
            {weakest && weakest.score <= 40 && (
              <li className="text-xs text-charcoal">{weakest.rating} for {weakest.label}</li>
            )}
            {provider.last_inspection_date && (() => {
              const days = Math.floor((Date.now() - new Date(provider.last_inspection_date).getTime()) / 86400000);
              return days > 730 ? <li className="text-xs text-charcoal">Not inspected in {Math.floor(days / 365)} years</li> : null;
            })()}
            {!aboveAvg && qualityScore && (
              <li className="text-xs text-charcoal">Below national average</li>
            )}
            {nearbyData && nearbyData.rank > nearbyData.total * 0.7 && (
              <li className="text-xs text-charcoal">Lower half locally</li>
            )}
          </ul>
        </div>
      </div>

      {/* Visit Questions */}
      {questions.length > 0 && (
        <div className="bg-cream border border-stone rounded-lg p-4 mb-4">
          <p className="text-sm font-semibold text-bark mb-2">Questions to Ask When You Visit</p>
          <ol className="space-y-2">
            {questions.slice(0, 3).map((q, i) => (
              <li key={i} className="text-xs text-charcoal flex gap-2">
                <span className="text-clay font-bold shrink-0">{i + 1}.</span>
                {q}
              </li>
            ))}
          </ol>
        </div>
      )}

      {/* Top Alternative */}
      {nearbyData?.topAlternative && (
        <div className="bg-parchment rounded-lg p-4 mb-4">
          <p className="text-xs font-semibold text-dusk mb-1">Highest-rated alternative nearby</p>
          <a
            href={`/provider/${nearbyData.topAlternative.slug}`}
            className="text-sm font-semibold text-clay hover:text-bark"
          >
            {nearbyData.topAlternative.name}
          </a>
          <span className="text-xs text-dusk ml-2">
            {nearbyData.topAlternative.overall_rating} · Score: {nearbyData.topAlternative.quality_score}/100
          </span>
        </div>
      )}

      {/* Share + Print */}
      <div className="flex gap-3 print:hidden">
        <button
          onClick={() => {
            const url = window.location.href.split("#")[0] + "#assessment";
            navigator.clipboard.writeText(url);
            const btn = document.getElementById("share-btn");
            if (btn) { btn.textContent = "Link copied!"; setTimeout(() => { btn.textContent = "Share assessment"; }, 2000); }
          }}
          id="share-btn"
          className="flex-1 py-2 text-sm font-medium border border-clay text-clay rounded-lg hover:bg-clay hover:text-white transition-colors"
        >
          Share assessment
        </button>
        <button
          onClick={() => window.print()}
          className="flex-1 py-2 text-sm font-medium bg-clay text-white rounded-lg hover:bg-bark transition-colors"
        >
          Print report
        </button>
      </div>

      <p className="text-xs text-dusk mt-3 text-center">
        Contains CQC data. Crown copyright and database right. Assessment by CareGist — independent, not pay-to-rank.
      </p>
    </div>
  );
}
