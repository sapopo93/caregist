const ratingColors: Record<string, string> = {
  Outstanding: "bg-moss text-white",
  Good: "bg-sage text-white",
  "Requires Improvement": "bg-amber text-white",
  Inadequate: "bg-alert text-white",
  "Not Yet Inspected": "bg-dusk text-white",
  "Inspected But Not Rated": "bg-dusk text-white",
  "No Published Rating": "bg-dusk text-white",
  "Insufficient Evidence To Rate": "bg-dusk text-white",
  Unknown: "bg-stone text-charcoal",
  "N/A": "bg-stone text-charcoal",
};

export default function RatingBadge({ rating }: { rating: string }) {
  const colorClass = ratingColors[rating] || "bg-stone text-charcoal";
  return (
    <span
      className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${colorClass}`}
      role="status"
      aria-label={`CQC rating: ${rating}`}
    >
      {rating}
    </span>
  );
}
