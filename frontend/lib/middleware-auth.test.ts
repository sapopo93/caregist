import { describe, it } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

describe("frontend auth middleware source", () => {
  const source = fs.readFileSync(new URL("../middleware.ts", import.meta.url), "utf-8");
  const rootLayoutSource = fs.readFileSync(new URL("../app/layout.tsx", import.meta.url), "utf-8");
  const cityRatingPages = [
    "../app/care-homes/[slug]/page.tsx",
    "../app/good-care-homes/[slug]/page.tsx",
    "../app/outstanding-care-homes/[slug]/page.tsx",
    "../app/requires-improvement-care-homes/[slug]/page.tsx",
  ].map((path) => fs.readFileSync(new URL(path, import.meta.url), "utf-8"));

  it("fails closed when backend session validation errors", () => {
    const catchBlock = source.match(/catch \(error\) \{[\s\S]*?\n  \}/)?.[0] ?? "";

    assert.match(catchBlock, /return redirectToLogin\(\)/);
    assert.doesNotMatch(catchBlock, /return NextResponse\.next\(\)/);
  });

  it("validates sessions against the current Vercel origin", () => {
    assert.match(source, /const apiUrl = request\.nextUrl\.origin/);
    assert.doesNotMatch(source, /process\.env\.API_URL\s*\|\|/);
  });

  it("uses the Node.js middleware runtime required by Vercel Services", () => {
    assert.match(source, /runtime:\s*["']nodejs["']/);
  });

  it("pairs nonce CSP with dynamic rendering so framework scripts receive nonces", () => {
    assert.match(source, /script-src 'self' 'nonce-\$\{nonce\}' 'strict-dynamic'/);
    const scriptSrcAssignments = source.match(/`script-src[^`]+`/g) ?? [];
    assert.ok(scriptSrcAssignments.length > 0);
    for (const directive of scriptSrcAssignments) {
      assert.doesNotMatch(directive, /'unsafe-inline'/);
    }
    assert.match(rootLayoutSource, /import \{ connection \} from "next\/server"/);
    assert.match(rootLayoutSource, /await connection\(\)/);
  });

  it("applies CSP middleware to the public /api page", () => {
    assert.match(source, /matcher:\s*\[[\s\S]*"\/api"/);
  });

  it("does not prerender nonce-dependent city rating pages", () => {
    for (const pageSource of cityRatingPages) {
      assert.match(pageSource, /export const dynamic = "force-dynamic"/);
      assert.doesNotMatch(pageSource, /generateStaticParams/);
    }
  });
});
