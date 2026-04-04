export default function GroupsLoading() {
  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      <div className="h-8 w-64 bg-stone rounded animate-pulse mb-6" />
      <div className="h-12 bg-cream border border-stone rounded-lg animate-pulse mb-8" />
      {[...Array(8)].map((_, i) => (
        <div key={i} className="h-14 bg-cream border-b border-stone animate-pulse" />
      ))}
    </div>
  );
}
