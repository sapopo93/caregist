/**
 * Serialise structured data for an inline <script type="application/ld+json">.
 *
 * JSON.stringify leaves "<" untouched, so a value containing "</script>" would
 * end the script element early and let the rest be parsed as HTML. Escaping
 * "<" (and the two JavaScript line separators) keeps the output valid JSON
 * while making that impossible, whatever the provider data contains.
 */
export function serialiseJsonLd(value: unknown): string {
  return JSON.stringify(value)
    .replace(/</g, "\\u003c")
    .replace(/[\u2028]/g, "\\u2028")
    .replace(/[\u2029]/g, "\\u2029");
}
