from tools.supply_snapshot import merge_dual_registrations


def _row(i, name, beds, rating):
    return {"id": i, "name": name, "postcode": "SL6 6JE", "beds": beds, "rating": rating}


def test_dual_registration_counted_once_keeping_rated_record():
    rows = [_row("a", "Clara Court", 76, "Not yet rated"), _row("b", "Clara Court", 76, "Outstanding"),
            _row("c", "Other Home", 76, "Good")]
    kept, merged = merge_dual_registrations(rows)
    assert [r["id"] for r in kept] == ["b", "c"]
    assert merged == ["a Clara Court merged into b"]


def test_different_bed_counts_are_not_merged():
    rows = [_row("a", "Same Name", 20, "Good"), _row("b", "Same Name", 21, "Good")]
    kept, merged = merge_dual_registrations(rows)
    assert len(kept) == 2 and merged == []
