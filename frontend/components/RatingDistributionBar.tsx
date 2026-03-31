const RATING_CONFIG: Record<string, { color: string; order: number }> = {
  Outstanding: { color: "bg-moss", order: 1 },
  Good: { color: "bg-amber", order: 2 },
  "Requires Improvement": { color: "bg-amber/50", order: 3 },
  Inadequate: { color: "bg-alert", order: 4 },
};

export default function RatingDistributionBar({
  distribution,
}: {
  distribution: Record<string, number>;
}) {
  const total = Object.values(distribution).reduce((a, b) => a + b, 0);
  if (total === 0) return null;

  const sorted = Object.entries(distribution)
    .filter(([rating]) => RATING_CONFIG[rating])
    .sort(([a], [b]) => (RATING_CONFIG[a]?.order ?? 99) - (RATING_CONFIG[b]?.order ?? 99));

  return (
    <div className="space-y-2">
      {sorted.map(([rating, count]) => {
        const pct = Math.round((count / total) * 100);
        const cfg = RATING_CONFIG[rating];
        return (
          <div key={rating} className="flex items-center gap-3">
            <span className="text-xs text-dusk w-40 shrink-0">{rating}</span>
            <div className="flex-1 bg-stone/30 rounded-full h-4 overflow-hidden">
              <div
                className={`h-full rounded-full ${cfg?.color || "bg-stone"}`}
                style={{ width: `${Math.max(pct, 2)}%` }}
              />
            </div>
            <span className="text-xs text-dusk w-16 text-right">
              {count} ({pct}%)
            </span>
          </div>
        );
      })}
    </div>
  );
}
