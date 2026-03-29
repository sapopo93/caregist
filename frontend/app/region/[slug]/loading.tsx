export default function Loading() {
  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      <div className="h-8 w-64 bg-cream rounded animate-pulse mb-2" />
      <div className="h-5 w-32 bg-cream rounded animate-pulse mb-6" />
      <div className="h-12 bg-cream rounded-lg animate-pulse mb-6" />
      <div className="grid gap-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-32 bg-cream rounded-lg animate-pulse" />
        ))}
      </div>
    </div>
  );
}
