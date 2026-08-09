import Link from "next/link";

interface Props {
  basePath: string;
  currentPage: number;
  totalPages: number;
  params: {
    q?: string;
    region?: string;
    service_type?: string;
    rating?: string;
    opportunity?: string;
  };
}

function buildPages(currentPage: number, totalPages: number): Array<number | string> {
  const pages = new Set<number>([1, totalPages, currentPage, currentPage - 1, currentPage + 1]);
  const sorted = [...pages].filter((page) => page >= 1 && page <= totalPages).sort((a, b) => a - b);
  const output: Array<number | string> = [];

  for (let index = 0; index < sorted.length; index += 1) {
    const page = sorted[index];
    const previous = sorted[index - 1];

    if (previous !== undefined && page - previous > 1) {
      output.push("…");
    }

    output.push(page);
  }

  return output;
}

export default function DirectoryPagination({ basePath, currentPage, totalPages, params }: Props) {
  if (totalPages <= 1) {
    return null;
  }

  const createHref = (page: number) => {
    const nextParams = new URLSearchParams();
    if (params.q) nextParams.set("q", params.q);
    if (params.region) nextParams.set("region", params.region);
    if (params.service_type) nextParams.set("service_type", params.service_type);
    if (params.rating) nextParams.set("rating", params.rating);
    if (params.opportunity) nextParams.set("opportunity", params.opportunity);
    if (page > 1) nextParams.set("page", String(page));
    const query = nextParams.toString();
    return query ? `${basePath}?${query}` : basePath;
  };

  const pages = buildPages(currentPage, totalPages);

  return (
    <nav className="mt-8 flex max-w-full flex-wrap items-center justify-center gap-2 overflow-x-hidden" aria-label="Pagination">
      <Link
        href={createHref(Math.max(currentPage - 1, 1))}
        aria-disabled={currentPage === 1}
        className={`rounded-xl px-3 py-2 text-sm font-medium sm:px-4 ${
          currentPage === 1
            ? "pointer-events-none border border-stone bg-parchment text-dusk/60"
            : "border border-stone bg-white text-bark hover:border-clay"
        }`}
      >
        Previous
      </Link>

      {pages.map((page, index) =>
        typeof page === "string" ? (
          <span key={`gap-${index}`} className="px-1 py-2 text-sm text-dusk sm:px-2">
            {page}
          </span>
        ) : (
          <Link
            key={page}
            href={createHref(page)}
            className={`rounded-xl px-3 py-2 text-sm font-medium sm:px-4 ${
              page === currentPage
                ? "bg-bark text-white"
                : "border border-stone bg-white text-bark hover:border-clay"
            }`}
          >
            {page}
          </Link>
        ),
      )}

      <Link
        href={createHref(Math.min(currentPage + 1, totalPages))}
        aria-disabled={currentPage === totalPages}
        className={`rounded-xl px-3 py-2 text-sm font-medium sm:px-4 ${
          currentPage === totalPages
            ? "pointer-events-none border border-stone bg-parchment text-dusk/60"
            : "border border-stone bg-white text-bark hover:border-clay"
        }`}
      >
        Next
      </Link>
    </nav>
  );
}
