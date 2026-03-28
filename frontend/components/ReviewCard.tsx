import StarRating from "./StarRating";

interface Review {
  id: number;
  rating: number;
  title: string;
  body: string;
  reviewer_name: string;
  relationship: string | null;
  visit_date: string | null;
  created_at: string;
}

const relationshipLabels: Record<string, string> = {
  family_member: "Family Member",
  service_user: "Service User",
  professional: "Professional",
  other: "Other",
};

export default function ReviewCard({ review }: { review: Review }) {
  const date = new Date(review.created_at).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });

  return (
    <div className="border border-stone rounded-lg p-5 bg-cream">
      <div className="flex items-start justify-between gap-3 mb-2">
        <div>
          <h4 className="font-semibold text-bark">{review.title}</h4>
          <div className="flex items-center gap-2 mt-1">
            <StarRating rating={review.rating} size="sm" />
            <span className="text-sm text-dusk">{review.rating}/5</span>
          </div>
        </div>
      </div>
      <p className="text-charcoal leading-relaxed mb-3">{review.body}</p>
      <div className="flex items-center gap-3 text-sm text-dusk">
        <span className="font-medium">{review.reviewer_name}</span>
        {review.relationship && (
          <span>· {relationshipLabels[review.relationship] || review.relationship}</span>
        )}
        <span className="ml-auto">{date}</span>
      </div>
    </div>
  );
}
