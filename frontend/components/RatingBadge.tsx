const ratingColors: Record<string, string> = {
  Outstanding: "bg-moss text-white",
  Good: "bg-sage text-white",
  "Requires Improvement": "bg-amber text-white",
  Inadequate: "bg-alert text-white",
  "Not Yet Inspected": "bg-dusk text-white",
  Unknown: "bg-stone text-charcoal",
};

export default function RatingBadge({ rating }: { rating: string }) {
  const colorClass = ratingColors[rating] || "bg-stone text-charcoal";
  return (
    <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${colorClass}`}>
      {rating}
    </span>
  );
}
