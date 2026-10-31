const STEPS = ["Inadequate", "Requires improvement", "Good", "Outstanding"] as const;
const STEP_COLOURS = ["bg-alert", "bg-amber", "bg-sage", "bg-moss"];

function stepIndex(rating: string | null | undefined) {
  const normal = (rating ?? "").trim().toLowerCase();
  return STEPS.findIndex((step) => step.toLowerCase() === normal);
}

/** One CQC rating on the four-step published scale. Unpublished values render an honest empty track. */
export default function RatingScale({ label, rating }: { label: string; rating: string | null | undefined }) {
  const index = stepIndex(rating);
  const published = index >= 0;
  return (
    <div className="grid grid-cols-[6.5rem_1fr] items-center gap-x-4 gap-y-1 sm:grid-cols-[7rem_1fr_9.5rem]">
      <p className="text-sm font-semibold text-bark">{label}</p>
      <div
        role="img"
        aria-label={published ? `${label}: ${STEPS[index]}` : `${label}: not published`}
        className="relative grid grid-cols-4 gap-1"
      >
        {STEPS.map((step, i) => (
          <span
            key={step}
            className={`h-2.5 rounded-full ${published && i <= index ? STEP_COLOURS[index] : "bg-stone/70"}`}
          />
        ))}
        {published ? (
          <span
            aria-hidden
            className={`absolute -top-1 h-4.5 w-1.5 rounded-sm bg-charcoal ring-2 ring-cream`}
            style={{ left: `calc(${index * 25 + 12.5}% - 3px)`, height: "1.125rem" }}
          />
        ) : null}
      </div>
      <p className="col-span-2 text-xs text-dusk sm:col-span-1 sm:text-right sm:text-sm">
        {published ? STEPS[index] : "Not published"}
      </p>
    </div>
  );
}
