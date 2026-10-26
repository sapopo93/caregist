/**
 * Labels for ratings served from CQC's published ratings file (migration 068)
 * rather than CQC's API. The date comes from the row (`rating_source_date`, the
 * date CQC published that rating), so no label names a fixed file edition.
 */

export const DISPUTED_FILE_RATING_NOTE =
  "CQC's ratings file lists a rating for this location, but CQC's own page no longer shows it, so none is displayed.";

/** "12 March 2025" for a YYYY-MM-DD date, or null when absent or unreadable. */
export function formatRatingSourceDate(value: string | null | undefined): string | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(value ?? "");
  if (!match) return null;
  const date = new Date(Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3])));
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" });
}

export function fileRatingNote(
  sourceDate: string | null | undefined,
  { notInApi = false }: { notInApi?: boolean } = {},
): string {
  const published = formatRatingSourceDate(sourceDate);
  const base = published
    ? `Rating per CQC's published ratings file (rating published ${published})`
    : "Rating per CQC's published ratings file";
  return notInApi ? `${base}; not yet returned by CQC's API.` : base;
}
