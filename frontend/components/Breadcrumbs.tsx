import Link from "next/link";

export interface Crumb {
  label: string;
  href?: string;
}

/** Region name to its /region/ slug, e.g. "Yorkshire & Humberside" to "yorkshire-humberside". */
export function regionSlug(region: string): string {
  return region.toLowerCase().replace(/&/g, "").trim().replace(/\s+/g, "-");
}

export default function Breadcrumbs({ crumbs }: { crumbs: Crumb[] }) {
  return (
    <nav aria-label="Breadcrumb" className="mb-4 text-sm text-dusk print:hidden">
      <ol className="flex flex-wrap items-center gap-x-2 gap-y-1">
        {crumbs.map((crumb, i) => {
          const last = i === crumbs.length - 1;
          return (
            <li key={`${crumb.label}-${i}`} className="inline-flex items-center gap-2">
              {crumb.href && !last ? (
                <Link href={crumb.href} className="font-medium text-clay underline-offset-2 hover:underline">
                  {crumb.label}
                </Link>
              ) : (
                <span aria-current={last ? "page" : undefined} className={last ? "max-w-[60ch] truncate font-semibold text-bark" : ""}>
                  {crumb.label}
                </span>
              )}
              {!last ? <span aria-hidden className="text-stone">›</span> : null}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
