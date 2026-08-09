/**
 * Convert a published website value into a safe absolute HTTP(S) URL.
 *
 * CQC source rows sometimes contain a bare hostname such as
 * `www.example.org`. Passing that value directly to an anchor makes the
 * browser treat it as a CareGist-relative path. Non-web schemes are rejected
 * so source data cannot create executable or credential-bearing links.
 */
export function normalizeExternalHttpUrl(value: string | null | undefined): string | null {
  const candidate = value?.trim();
  if (!candidate) return null;

  const absoluteCandidate = /^[a-z][a-z0-9+.-]*:/i.test(candidate)
    ? candidate
    : `https://${candidate.replace(/^\/+/, "")}`;

  try {
    const url = new URL(absoluteCandidate);
    if (url.protocol !== "http:" && url.protocol !== "https:") return null;
    if (!url.hostname || url.username || url.password) return null;
    return url.toString();
  } catch {
    return null;
  }
}
