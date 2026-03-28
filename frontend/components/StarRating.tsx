"use client";

interface StarRatingProps {
  rating: number;
  max?: number;
  interactive?: boolean;
  onChange?: (rating: number) => void;
  size?: "sm" | "md" | "lg";
}

export default function StarRating({
  rating,
  max = 5,
  interactive = false,
  onChange,
  size = "md",
}: StarRatingProps) {
  const sizeClass = { sm: "w-4 h-4", md: "w-5 h-5", lg: "w-7 h-7" }[size];

  return (
    <div className="inline-flex items-center gap-0.5" role="img" aria-label={`${rating} out of ${max} stars`}>
      {Array.from({ length: max }, (_, i) => {
        const filled = i < rating;
        return (
          <button
            key={i}
            type="button"
            disabled={!interactive}
            onClick={() => interactive && onChange?.(i + 1)}
            className={`${interactive ? "cursor-pointer hover:scale-110 transition-transform" : "cursor-default"} focus:outline-none`}
            aria-label={interactive ? `Rate ${i + 1} star${i === 0 ? "" : "s"}` : undefined}
            tabIndex={interactive ? 0 : -1}
          >
            <svg className={sizeClass} viewBox="0 0 20 20" fill={filled ? "currentColor" : "none"} stroke="currentColor" strokeWidth={filled ? 0 : 1.5}>
              <path
                d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.286 3.957a1 1 0 00.95.69h4.162c.969 0 1.371 1.24.588 1.81l-3.37 2.448a1 1 0 00-.364 1.118l1.287 3.957c.3.921-.755 1.688-1.54 1.118l-3.37-2.448a1 1 0 00-1.176 0l-3.37 2.448c-.784.57-1.838-.197-1.539-1.118l1.287-3.957a1 1 0 00-.364-1.118L2.063 9.384c-.783-.57-.38-1.81.588-1.81h4.162a1 1 0 00.95-.69l1.286-3.957z"
                className={filled ? "text-amber" : "text-stone"}
              />
            </svg>
          </button>
        );
      })}
    </div>
  );
}
