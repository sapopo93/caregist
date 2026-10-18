"""Turn the CQC directory export into map points for the launch video.

Writes data/points.json: every active England location projected to a flat
plane (x, y in kilometres-ish), tagged with region, plus per-region counts.
Run: python3 marketing/launch-video/data/prepare_points.py
"""

import csv
import json
import math
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "directory_providers.csv"
OUT = Path(__file__).resolve().parent / "points.json"

# Equirectangular projection centred on England.
LAT0, LON0 = 52.8, -1.6
KM_PER_DEG = 111.32


def project(lat: float, lon: float) -> tuple[float, float]:
    x = (lon - LON0) * KM_PER_DEG * math.cos(math.radians(LAT0))
    y = (lat - LAT0) * KM_PER_DEG
    return round(x, 2), round(y, 2)


def main() -> None:
    csv.field_size_limit(sys.maxsize)
    points = []
    regions = Counter()
    with SRC.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if (row.get("status") or "").lower() not in ("", "active", "registered"):
                continue
            try:
                lat, lon = float(row["latitude"]), float(row["longitude"])
            except (TypeError, ValueError):
                continue
            if not (49.8 < lat < 55.9 and -6.5 < lon < 2.0):
                continue
            region = (row.get("region") or "Unknown").strip()
            x, y = project(lat, lon)
            points.append([x, y, region])
            regions[region] += 1

    OUT.write_text(json.dumps({"points": points, "regions": dict(regions.most_common())}))
    print(f"{len(points)} points -> {OUT}")
    for name, count in regions.most_common():
        print(f"  {name}: {count}")


if __name__ == "__main__":
    main()
