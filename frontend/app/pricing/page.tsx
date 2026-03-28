import Link from "next/link";

const plans = [
  {
    name: "Free",
    price: "£0",
    period: "forever",
    features: [
      "100 API requests/minute",
      "Full provider search",
      "Basic provider details",
      "Community support",
    ],
    cta: "Get Started",
    href: "/signup",
    featured: false,
  },
  {
    name: "Starter",
    price: "£49",
    period: "/month",
    features: [
      "1,000 API requests/minute",
      "Full provider search + nearby",
      "CSV export (10,000 rows)",
      "All provider fields",
      "Email support",
    ],
    cta: "Start Free Trial",
    href: "/signup?plan=starter",
    featured: true,
  },
  {
    name: "Pro",
    price: "£199",
    period: "/month",
    features: [
      "5,000 API requests/minute",
      "Everything in Starter",
      "Bulk data export",
      "Webhook notifications",
      "Priority support",
      "Custom integrations",
    ],
    cta: "Contact Us",
    href: "/signup?plan=pro",
    featured: false,
  },
];

export default function PricingPage() {
  return (
    <div className="max-w-5xl mx-auto px-6 py-16">
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold mb-4">Simple, transparent pricing</h1>
        <p className="text-dusk text-lg" style={{ fontFamily: "Lora" }}>
          Access 55,818 CQC-rated care providers via API. Start free, upgrade when you need more.
        </p>
      </div>

      <div className="grid md:grid-cols-3 gap-6">
        {plans.map((plan) => (
          <div
            key={plan.name}
            className={`rounded-xl p-8 ${
              plan.featured
                ? "bg-bark text-cream border-2 border-clay shadow-lg scale-105"
                : "bg-cream border border-stone"
            }`}
          >
            <h2 className={`text-xl font-bold mb-2 ${plan.featured ? "text-cream" : "text-bark"}`}>
              {plan.name}
            </h2>
            <div className="mb-6">
              <span className={`text-4xl font-bold ${plan.featured ? "text-amber" : "text-clay"}`}>
                {plan.price}
              </span>
              <span className={`text-sm ${plan.featured ? "text-stone" : "text-dusk"}`}>
                {plan.period}
              </span>
            </div>
            <ul className="space-y-3 mb-8">
              {plan.features.map((f) => (
                <li key={f} className={`text-sm ${plan.featured ? "text-stone" : "text-dusk"}`}>
                  <span className={plan.featured ? "text-amber" : "text-moss"}>&#10003;</span> {f}
                </li>
              ))}
            </ul>
            <Link
              href={plan.href}
              className={`block text-center py-3 rounded-lg font-medium transition-colors ${
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

      <div className="text-center mt-12 text-sm text-dusk">
        <p>All plans include CQC data attribution. Data refreshed weekly.</p>
        <p className="mt-1">Need a custom plan? <a href="mailto:hello@caregist.co.uk" className="text-clay underline">Contact us</a></p>
      </div>
    </div>
  );
}
