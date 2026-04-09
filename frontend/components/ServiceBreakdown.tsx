/**
 * Categorises CQC service types, specialisms, and regulated activities
 * into meaningful groups for families browsing provider profiles.
 */

const SERVICE_CATEGORIES: Record<string, { label: string; icon: string; members: string[] }> = {
  residential: {
    label: "Residential Care",
    icon: "🏠",
    members: [
      "Care Home Service With Nursing",
      "Care Home Service Without Nursing",
      "Extra Care Housing",
    ],
  },
  homecare: {
    label: "Home Care",
    icon: "🏡",
    members: [
      "Domiciliary Care Service",
    ],
  },
  community: {
    label: "Community & Supported Living",
    icon: "🤝",
    members: [
      "Supported Living",
      "Shared Lives",
      "Community Healthcare",
    ],
  },
};

const SPECIALISM_CATEGORIES: Record<string, { label: string; icon: string; members: string[] }> = {
  conditions: {
    label: "Conditions Supported",
    icon: "💊",
    members: [
      "Dementia",
      "Mental Health",
      "Substance Misuse",
    ],
  },
  needs: {
    label: "Care Needs",
    icon: "♿",
    members: [
      "Physical Disabilities",
      "Learning Disabilities",
      "Sensory Impairments",
    ],
  },
  groups: {
    label: "Age Groups",
    icon: "👥",
    members: [
      "Older People",
    ],
  },
};

function categorise(
  items: string[],
  categories: Record<string, { label: string; icon: string; members: string[] }>
): { category: string; label: string; icon: string; matched: string[] }[] {
  const result: { category: string; label: string; icon: string; matched: string[] }[] = [];

  for (const [key, cat] of Object.entries(categories)) {
    const matched = items.filter((item) =>
      cat.members.some((m) => m.toLowerCase() === item.toLowerCase())
    );
    if (matched.length > 0) {
      result.push({ category: key, label: cat.label, icon: cat.icon, matched });
    }
  }

  // Catch any uncategorised items
  const allMatched = result.flatMap((r) => r.matched.map((m) => m.toLowerCase()));
  const uncategorised = items.filter((item) => !allMatched.includes(item.toLowerCase()));
  if (uncategorised.length > 0) {
    result.push({ category: "other", label: "Other Services", icon: "📋", matched: uncategorised });
  }

  return result;
}

interface ServiceBreakdownProps {
  serviceTypes: string | null;
  specialisms: string | null;
  regulatedActivities: string | null;
}

export default function ServiceBreakdown({ serviceTypes, specialisms, regulatedActivities }: ServiceBreakdownProps) {
  const services = serviceTypes?.split("|").filter(Boolean) || [];
  const specs = specialisms?.split("|").filter(Boolean) || [];
  const activities = regulatedActivities?.split("|").filter(Boolean) || [];

  if (services.length === 0 && specs.length === 0) return null;

  const serviceCats = categorise(services, SERVICE_CATEGORIES);
  const specCats = categorise(specs, SPECIALISM_CATEGORIES);

  return (
    <div className="bg-cream border border-stone rounded-lg p-6 mb-6" id="care-provided">
      <h2 className="text-xl font-bold mb-4">Care Provided</h2>

      {serviceCats.length > 0 && (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-4">
          {serviceCats.map((cat) => (
            <div key={cat.category} className="bg-parchment rounded-lg p-4">
              <p className="font-semibold text-bark mb-2">
                <span className="mr-1.5">{cat.icon}</span>{cat.label}
              </p>
              <ul className="space-y-1">
                {cat.matched.map((s) => (
                  <li key={s} className="text-sm text-charcoal flex items-start gap-1.5">
                    <span className="text-moss mt-0.5 shrink-0">&#10003;</span>
                    <span>{s}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}

      {specCats.length > 0 && (
        <>
          <h3 className="text-sm font-semibold text-dusk mb-3 mt-2">Specialisms</h3>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-4">
            {specCats.map((cat) => (
              <div key={cat.category} className="bg-parchment rounded-lg p-4">
                <p className="font-semibold text-bark mb-2">
                  <span className="mr-1.5">{cat.icon}</span>{cat.label}
                </p>
                <ul className="space-y-1">
                  {cat.matched.map((s) => (
                    <li key={s} className="text-sm text-charcoal flex items-start gap-1.5">
                      <span className="text-moss mt-0.5 shrink-0">&#10003;</span>
                      <span>{s}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </>
      )}

      {activities.length > 0 && (
        <div className="border-t border-stone pt-3 mt-2">
          <p className="text-xs text-dusk mb-2 font-semibold">CQC-regulated for:</p>
          <div className="flex flex-wrap gap-1.5">
            {activities.map((a) => (
              <span key={a} className="bg-moss/10 text-moss text-xs px-2.5 py-1 rounded-full border border-moss/20">
                {a}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
