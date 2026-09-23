import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { resolve } from "node:path";

const appRoot = resolve(import.meta.dirname, "..");

function walk(dir: string): string[] {
  const entries = readdirSync(dir);
  const files: string[] = [];
  for (const entry of entries) {
    const full = resolve(dir, entry);
    const stat = statSync(full);
    if (stat.isDirectory()) {
      files.push(...walk(full));
    } else if (/\.(ts|tsx)$/.test(entry)) {
      files.push(full);
    }
  }
  return files;
}

describe("no remote fonts", () => {
  it("never imports next/font/google from app/ or components/", () => {
    const offenders: string[] = [];
    for (const dir of ["app", "components"]) {
      for (const file of walk(resolve(appRoot, dir))) {
        const source = readFileSync(file, "utf8");
        if (source.includes("next/font/google")) {
          offenders.push(file);
        }
      }
    }
    assert.deepEqual(offenders, []);
  });
});
