#!/usr/bin/env python3
"""Populate group_name column from provider_groups.csv."""

import csv
import sys
import psycopg2

def main():
    db_url = sys.argv[1] if len(sys.argv) > 1 else "postgresql://caregist:caregist_dev@localhost:5432/caregist"
    csv_path = sys.argv[2] if len(sys.argv) > 2 else "provider_groups.csv"

    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    with open(csv_path) as f:
        reader = csv.DictReader(f)
        batch = []
        count = 0
        for row in reader:
            batch.append((row["group_name"], row["provider_id"]))
            if len(batch) >= 1000:
                cur.executemany(
                    "UPDATE care_providers SET group_name = %s WHERE provider_id = %s",
                    batch,
                )
                conn.commit()
                count += len(batch)
                batch = []
                print(f"  Updated {count} rows...")

        if batch:
            cur.executemany(
                "UPDATE care_providers SET group_name = %s WHERE provider_id = %s",
                batch,
            )
            conn.commit()
            count += len(batch)

    print(f"Done. Updated {count} provider rows with group names.")
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
