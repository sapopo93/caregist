export default function SearchLoading() {
  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      <div className="h-12 bg-stone rounded-lg animate-pulse mb-8 max-w-2xl" />
      <div className="flex gap-8">
        <div className="hidden md:block w-56 flex-shrink-0 space-y-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-16 bg-stone rounded-lg animate-pulse" />
          ))}
        </div>
        <div className="flex-1 space-y-4">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-28 bg-cream border border-stone rounded-lg animate-pulse" />
          ))}
        </div>
      </div>
    </div>
  );
}
