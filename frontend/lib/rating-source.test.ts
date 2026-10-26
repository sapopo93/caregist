import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { describe, it } from "node:test";

import { fileRatingNote, formatRatingSourceDate } from "./rating-source.ts";

describe("ratings-file labels", () => {
  it("states the rating's own CQC publication date", () => {
    assert.equal(
      fileRatingNote("2025-03-12"),
      "Rating per CQC's published ratings file (rating published 12 March 2025)",
    );
    assert.equal(
      fileRatingNote("2025-03-12", { notInApi: true }),
      "Rating per CQC's published ratings file (rating published 12 March 2025); not yet returned by CQC's API.",
    );
  });

  it("omits the date rather than inventing one", () => {
    assert.equal(fileRatingNote(null), "Rating per CQC's published ratings file");
    assert.equal(formatRatingSourceDate("not a date"), null);
    assert.equal(formatRatingSourceDate(undefined), null);
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
    }
  });
});
