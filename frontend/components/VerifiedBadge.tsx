export default function VerifiedBadge({ size = "sm" }: { size?: "sm" | "md" }) {
  const cls = size === "md" ? "text-sm px-2.5 py-1" : "text-xs px-2 py-0.5";
  return (
    <span
      className={`inline-flex items-center gap-1 bg-moss/10 text-moss border border-moss/30 rounded-full font-medium ${cls}`}
      role="status"
      aria-label="Verified provider"
    >
      <svg className={size === "md" ? "w-4 h-4" : "w-3 h-3"} viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
        <path
          fillRule="evenodd"
          d="M16.403 12.652a3 3 0 010-5.304 3 3 0 00-1.06-1.06 3 3 0 01-5.304 0 3 3 0 00-1.06 1.06 3 3 0 010 5.304 3 3 0 001.06 1.06 3 3 0 015.304 0 3 3 0 001.06-1.06zM12.95 10.707l-2.122-2.122a.75.75 0 00-1.06 1.06l2.652 2.652a.75.75 0 001.06 0l4.243-4.242a.75.75 0 00-1.06-1.061L12.95 10.707z"
          clipRule="evenodd"
        />
      </svg>
      Verified
    </span>
  );
}
