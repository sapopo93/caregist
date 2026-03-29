import ReviewCard from "./ReviewCard";
import ReviewForm from "./ReviewForm";
import StarRating from "./StarRating";

interface ReviewsSectionProps {
  slug: string;
  reviews: any[];
  summary: { count: number; avg_rating: number | null };
  providerName: string;
}

export default function ReviewsSection({ slug, reviews, summary, providerName }: ReviewsSectionProps) {
  return (
    <div className="bg-cream border border-stone rounded-lg p-6 mb-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold">Community Reviews</h2>
        {summary.count > 0 && summary.avg_rating && (
          <div className="flex items-center gap-2">
            <StarRating rating={Math.round(summary.avg_rating)} size="sm" />
            <span className="text-sm text-dusk">
              {summary.avg_rating} ({summary.count} review{summary.count !== 1 ? "s" : ""})
            </span>
          </div>
        )}
      </div>

      {reviews.length > 0 ? (
        <div className="space-y-4 mb-6">
          {reviews.map((review: any) => (
            <ReviewCard key={review.id} review={review} />
          ))}
        </div>
      ) : (
        <p className="text-dusk mb-6">No reviews yet. Be the first to share your experience.</p>
      )}

      <div className="border-t border-stone pt-6">
        <h3 className="text-lg font-semibold mb-3">Share your experience with {providerName}</h3>
        <ReviewForm slug={slug} />
      </div>
    </div>
  );
}
