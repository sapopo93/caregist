export default function ProviderLoading() {
  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      <div className="flex justify-between items-start mb-8">
        <div className="h-10 w-64 bg-stone rounded animate-pulse" />
        <div className="h-8 w-20 bg-stone rounded-full animate-pulse" />
      </div>
      <div className="h-40 bg-cream border border-stone rounded-lg animate-pulse mb-6" />
      <div className="grid md:grid-cols-2 gap-6 mb-6">
        <div className="h-48 bg-cream border border-stone rounded-lg animate-pulse" />
        <div className="h-48 bg-cream border border-stone rounded-lg animate-pulse" />
      </div>
      <div className="h-32 bg-cream border border-stone rounded-lg animate-pulse" />
    </div>
  );
}
