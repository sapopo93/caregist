/**
 * Labels naming the source of every displayed rating (the CareGist rating rule):
 * CQC's published ratings file is the main source, a later check of CQC's own page
 * wins where it differs, and CQC's API fills only the file's gaps. The date comes
 * from the row (`rating_source_date`), so no label names a fixed file edition.
 */

/** "12 March 2025" for a YYYY-MM-DD date, or null when absent or unreadable. */
export function formatRatingSourceDate(value: string | null | undefined): string | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(value ?? "");
  if (!match) return null;
  const date = new Date(Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3])));
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" });
}

/** The label for a rating's source, or null when no source served one. */
export function ratingSourceNote(
  source: string | null | undefined,
  sourceDate: string | null | undefined,
): string | null {
  const when = formatRatingSourceDate(sourceDate);
  switch (source) {
    case "cqc_file":
      return when
        ? `Rating per CQC's published ratings file (rating published ${when})`
        : "Rating per CQC's published ratings file";
    case "cqc_website":
      return when
        ? `Rating per CQC's own website, checked ${when}; newer than CQC's ratings file`
        : "Rating per CQC's own website; newer than CQC's ratings file";
    case "cqc_website_unrated":
      return "CQC's own website shows no current rating for this location, so none is displayed.";
    case "cqc_api":
      return when
        ? `Rating per CQC's API (rating published ${when}); not in CQC's ratings file yet`
        : "Rating per CQC's API; not in CQC's ratings file yet";
    default:
      return null;
  }
}
