export default function AeoBlock({
  name,
  type,
  town,
  rating,
  inspectionDate,
}: {
  name: string;
  type?: string | null;
  town?: string | null;
  rating?: string | null;
  inspectionDate?: string | null;
}) {
  const serviceType = type || "care provider";
  const location = town || "England";
  const ratingText = rating || "Not Yet Inspected";
  const dateText = inspectionDate
    ? new Date(inspectionDate).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" })
    : null;

  return (
    <section className="bg-parchment border-b border-stone px-6 py-4 text-sm text-charcoal leading-relaxed">
      <p>
        {name} is a CQC-registered {serviceType.toLowerCase()} based in {location}.
        {" "}Their current rating is <strong>{ratingText}</strong>
        {dateText ? <>, awarded following an inspection on {dateText}.</> : "."}
      </p>
    </section>
  );
}
