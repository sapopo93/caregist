const fs = require("node:fs");
const path = require("node:path");

const datasetPath = path.join(__dirname, "..", "data", "directory-fallback-full.csv");
const requiredColumns = [
  "id",
  "slug",
  "name",
  "status",
  "region",
  "service_types",
  "overall_rating",
  "inspection_report_url",
];

function fail(message) {
  console.error(`Directory fallback verification failed: ${message}`);
  process.exit(1);
}

if (!fs.existsSync(datasetPath)) {
  fail(`missing ${datasetPath}`);
}

const stats = fs.statSync(datasetPath);
if (stats.size < 10 * 1024 * 1024) {
  fail(`expected a full fallback dataset at ${datasetPath}, found only ${stats.size} bytes`);
}

const fileHandle = fs.openSync(datasetPath, "r");
const buffer = Buffer.alloc(8192);
const bytesRead = fs.readSync(fileHandle, buffer, 0, buffer.length, 0);
fs.closeSync(fileHandle);

const headerLine = buffer
  .subarray(0, bytesRead)
  .toString("utf8")
  .split(/\r?\n/, 1)[0]
  .trim();

if (!headerLine) {
  fail(`could not read CSV header from ${datasetPath}`);
}

const headerColumns = new Set(headerLine.split(",").map((column) => column.trim()));
for (const column of requiredColumns) {
  if (!headerColumns.has(column)) {
    fail(`missing required CSV column "${column}" in ${datasetPath}`);
  }
}

console.log(`Directory fallback verification passed: ${datasetPath} (${Math.round(stats.size / (1024 * 1024))} MB)`);
