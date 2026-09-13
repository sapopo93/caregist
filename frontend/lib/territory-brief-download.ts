import { createHash } from "node:crypto";

export interface TerritoryBriefDownload {
  blob_pathname: string;
  filename: string;
  content_type: string;
}

type Query = (sql: string, values: string[]) => Promise<{ rows: TerritoryBriefDownload[] }>;

/** Atomically consume an entitlement, never exposing unpaid or refunded packs. */
export async function consumeTerritoryBriefDownload(token: string, query: Query): Promise<TerritoryBriefDownload | null> {
  if (!/^[A-Za-z0-9_-]{43}$/.test(token)) return null;
  const hash = createHash("sha256").update(token, "utf8").digest("hex");
  const result = await query(`
    WITH consumed AS (
      UPDATE territory_brief_download_tokens AS token
      SET download_count = token.download_count + 1, last_downloaded_at = NOW()
      FROM territory_brief_orders AS purchase
      WHERE token.token_hash = $1
        AND token.order_id = purchase.id
        AND token.expires_at > NOW()
        AND token.download_count < token.max_downloads
        AND purchase.status = 'fulfilled'
        AND CASE token.artifact_kind
          WHEN 'pdf' THEN purchase.blob_pdf_pathname
          WHEN 'csv' THEN purchase.blob_csv_pathname
        END IS NOT NULL
      RETURNING token.artifact_kind,
        CASE token.artifact_kind
          WHEN 'pdf' THEN purchase.blob_pdf_pathname
          WHEN 'csv' THEN purchase.blob_csv_pathname
        END AS blob_pathname
    )
    SELECT blob_pathname,
      'territory-opportunity-brief.' || artifact_kind AS filename,
      CASE artifact_kind WHEN 'pdf' THEN 'application/pdf'
        ELSE 'text/csv; charset=utf-8' END AS content_type
    FROM consumed
  `, [hash]);
  return result.rows[0] ?? null;
}
