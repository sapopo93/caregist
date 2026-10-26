import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { describe, it } from "node:test";

import { formatRatingSourceDate, ratingSourceNote } from "./rating-source.ts";

describe("rating source labels", () => {
  it("names each source with its own date", () => {
    assert.equal(
      ratingSourceNote("cqc_file", "2025-03-12"),
      "Rating per CQC's published ratings file (rating published 12 March 2025)",
    );
    assert.equal(
      ratingSourceNote("cqc_website", "2026-10-20"),
      "Rating per CQC's own website, checked 20 October 2026; newer than CQC's ratings file",
    );
    assert.equal(
      ratingSourceNote("cqc_api", "2026-10-21"),
      "Rating per CQC's API (rating published 21 October 2026); not in CQC's ratings file yet",
    );
    assert.match(ratingSourceNote("cqc_website_unrated", null) ?? "", /shows no current rating/);
  });

  it("omits the date rather than inventing one, and labels nothing without a source", () => {
    assert.equal(ratingSourceNote("cqc_file", null), "Rating per CQC's published ratings file");
    assert.equal(ratingSourceNote(null, "2026-10-20"), null);
    assert.equal(formatRatingSourceDate("not a date"), null);
  });

  it("no rating label hardcodes a ratings-file edition date", () => {
    for (const path of [
      "app/page.tsx",
      "app/provider/[slug]/page.tsx",
      "components/ProviderCard.tsx",
      "components/directory/DirectoryProviderCard.tsx",
    ]) {
      const source = readFileSync(new URL(`../${path}`, import.meta.url), "utf8");
      assert.doesNotMatch(source, /ratings file \(\d{1,2} \w+ \d{4}\)/, path);
      assert.doesNotMatch(source, /cqc_file_disputed/, path);
    }
  });
});
