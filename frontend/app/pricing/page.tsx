import Link from "next/link";

const plans = [
  {
    name: "Free",
    price: "£0",
    period: "forever",
    best: "Families & evaluation",
    features: [
      "150 searches per day",
      "4,500 per month",
      "Basic provider info (name, rating, town)",
      "5 results per page",
    ],
    limits: [
      "Phone & email hidden",
      "No map coordinates",
      "No nearby search",
      "No CSV export",
      "No comparison",
    ],
    cta: "Get Started",
    href: "/signup",
    featured: false,
  },
  {
    name: "Starter",
    price: "£19",
    period: "/month",
    best: "Professionals & daily use",
    features: [
      "500 searches per day",
      "10,000 per month",
      "All provider fields (phone, email, coordinates)",
      "20 results per page",
      "Nearby search by postcode",
      "CSV export (500 rows)",
      "Compare up to 3 providers",
      "Key question ratings (Safe, Effective, etc.)",
      "Email support (72h)",
    ],
    limits: [],
    cta: "Start Free Trial",
    href: "/signup?plan=starter",
    featured: true,
  },
  {
    name: "Pro",
    price: "£49",
    period: "/month",
    best: "Small teams & reports",
    features: [
      "Everything in Starter",
      "2,000 searches per day",
      "50,000 per month",
      "50 results per page",
      "CSV export (5,000 rows)",
      "Compare up to 5 providers",
      "Email support (48h)",
    ],
    limits: [],
    cta: "Upgrade to Pro",
    href: "/signup?plan=pro",
    featured: false,
  },
  {
    name: "Business",
    price: "£149",
    period: "/month",
    best: "Platforms & integration",
    features: [
      "Everything in Pro",
      "10,000 searches per day",
      "250,000 per month",
      "100 results per page",
      "CSV export (10,000+ rows)",
      "Compare up to 10 providers",
      "Webhook alerts (rating changes)",
      "Full data fields (metadata, timestamps)",
      "Email support (24h) + onboarding call",
    ],
    limits: [],
    cta: "Go Business",
    href: "/signup?plan=business",
    featured: false,
  },
];

export default function PricingPage() {
  return (
    <div className="max-w-6xl mx-auto px-6 py-16">
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold mb-4">Simple, transparent pricing</h1>
        <p className="text-dusk text-lg" style={{ fontFamily: "Lora" }}>
          Access 55,818 CQC-rated care providers. Start free, upgrade when you need more.
        </p>
      </div>

      <div className="grid md:grid-cols-4 gap-5">
        {plans.map((plan) => (
          <div
            key={plan.name}
            className={`rounded-xl p-6 flex flex-col ${
              plan.featured
                ? "bg-bark text-cream border-2 border-clay shadow-lg md:scale-105"
                : "bg-cream border border-stone"
            }`}
          >
            <div className="mb-1">
              <h2 className={`text-lg font-bold ${plan.featured ? "text-cream" : "text-bark"}`}>
                {plan.name}
              </h2>
              <p className={`text-xs ${plan.featured ? "text-stone" : "text-dusk"}`}>{plan.best}</p>
            </div>
            <div className="mb-5 mt-3">
              <span className={`text-3xl font-bold ${plan.featured ? "text-amber" : "text-clay"}`}>
                {plan.price}
              </span>
              <span className={`text-sm ${plan.featured ? "text-stone" : "text-dusk"}`}>
                {plan.period}
              </span>
            </div>
            <ul className="space-y-2 mb-4 flex-1">
              {plan.features.map((f) => (
                <li key={f} className={`text-xs ${plan.featured ? "text-stone" : "text-dusk"}`}>
                  <span className={plan.featured ? "text-amber" : "text-moss"}>&#10003;</span> {f}
                </li>
              ))}
              {plan.limits.map((l) => (
                <li key={l} className={`text-xs ${plan.featured ? "text-dusk" : "text-stone"}`}>
                  <span className="text-alert">&#10007;</span> {l}
                </li>
              ))}
            </ul>
            <Link
              href={plan.href}
              className={`block text-center py-2.5 rounded-lg font-medium text-sm transition-colors ${
                plan.featured
                  ? "bg-clay text-white hover:bg-amber"
                  : "border border-clay text-clay hover:bg-clay hover:text-white"
              }`}
            >
              {plan.cta}
            </Link>
          </div>
        ))}
      </div>

      <div className="text-center mt-10">
        <p className="text-bark font-semibold mb-2">Need more? Enterprise plans start at £500/month</p>
        <p className="text-sm text-dusk">
          Unlimited API calls, SLA guarantee, dedicated support, custom data feeds, and DPA.{" "}
          <a href="mailto:enterprise@caregist.co.uk" className="text-clay underline">Contact us</a>
        </p>
      </div>

      <div className="text-center mt-6 text-xs text-dusk">
        All plans include CQC data attribution. Data refreshed weekly. Cancel anytime.
      </div>
    </div>
  );
}
