type Step = { label: string; value?: string | null; display: string };

function dayGap(from?: string | null, to?: string | null): number | null {
  if (!from || !to) return null;
  const a = new Date(from).getTime();
  const b = new Date(to).getTime();
  if (Number.isNaN(a) || Number.isNaN(b)) return null;
  return Math.max(0, Math.round((b - a) / 86_400_000));
}

function gapLabel(days: number | null): string {
  if (days === null) return "gap unknown";
  if (days === 0) return "same day";
  return `${days} day${days === 1 ? "" : "s"} later`;
}

/** Published → retrieved → reconciled, with the real day gaps. Never fills a missing date. */
export default function SourceTimeline({
  steps,
  coverage,
}: {
  steps: Step[];
  coverage?: number | null;
}) {
  return (
    <div className="mb-6">
      <ol className="grid gap-4 sm:grid-cols-3">
        {steps.map((step, i) => (
          <li key={step.label} className="relative">
            <div className="flex items-center gap-2">
              <span
                aria-hidden
                className={`h-3 w-3 rounded-full border-2 ${step.value ? "border-clay bg-clay" : "border-stone bg-white"}`}
              />
              {i < steps.length - 1 ? <span aria-hidden className="hidden h-px flex-1 bg-stone sm:block" /> : null}
            </div>
            <p className="mt-2 text-xs uppercase tracking-wide text-dusk">{step.label}</p>
            <p className="text-sm font-semibold text-bark">{step.display}</p>
            {i > 0 ? (
              <p className="text-xs text-dusk">{gapLabel(dayGap(steps[i - 1].value, step.value))}</p>
            ) : null}
          </li>
        ))}
      </ol>
      {coverage != null ? (
        <div className="mt-5">
          <div className="flex justify-between text-xs text-dusk">
            <span>Coverage of source locations checked</span>
            <span className="font-mono font-bold text-charcoal">{coverage}%</span>
          </div>
          <div
            role="img"
            aria-label={`Coverage ${coverage} percent`}
            className="mt-1 h-2 overflow-hidden rounded-full bg-stone/60"
          >
            <div className="h-full rounded-full bg-moss" style={{ width: `${Math.min(100, Math.max(0, coverage))}%` }} />
          </div>
        </div>
      ) : null}
    </div>
  );
}
