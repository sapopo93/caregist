from datetime import date

from api.services.registration_endings import (
    CONFIRMED_CLOSURE,
    DORMANT,
    RE_REGISTRATION,
    UNRESOLVED,
    EndingIndex,
    classifier_for_export,
    classify_ending,
)


def _ended(lid="1-old", **kw):
    row = {"locationId": lid, "name": "Rose Court", "postalCode": "AB1 2CD",
           "registrationStatus": "Deregistered", "deregistrationDate": "2026-06-01",
           "registrationDate": "2012-01-01", "dormancy": "N", "relationships": []}
    row.update(kw)
    return row


def _live(lid="1-new", **kw):
    row = {"locationId": lid, "name": "Rose Court", "postalCode": "AB1 2CD",
           "registrationStatus": "Registered", "registrationDate": "2026-06-02", "dormancy": "N",
           "relationships": []}
    row.update(kw)
    return row


def test_registered_location_has_no_ending():
    assert classify_ending(_live(), EndingIndex.build([])) is None


def test_confirmed_closure():
    e = classify_ending(_ended(), EndingIndex.build([_ended()]))
    assert (e.ending_class, e.end_date) == (CONFIRMED_CLOSURE, date(2026, 6, 1))


def test_successor_link_on_ended_location_is_ownership_change():
    row = _ended(relationships=[{"type": "HSCA Successor", "reason": "New Provider",
                                 "relatedLocationId": "1-new"}])
    e = classify_ending(row, EndingIndex.build([row, _live()]))
    assert (e.ending_class, e.kind, e.successor_ids, e.successors_in_data) == (
        RE_REGISTRATION, "ownership_change", ("1-new",), ("1-new",),
    )


def test_predecessor_link_on_successor_side_also_counts():
    succ = _live(name="Different", relationships=[{"type": "HSCA Predecessor", "reason": "Location Move",
                                                   "relatedLocationId": "1-old"}])
    e = classify_ending(_ended(), EndingIndex.build([_ended(), succ]))
    assert (e.ending_class, e.kind, e.successor_ids) == (RE_REGISTRATION, "location_move", ("1-new",))


def test_successor_missing_from_data_is_still_linked_but_flagged():
    row = _ended(relationships=[{"type": "HSCA Successor", "reason": "Legal Entity Change",
                                 "relatedLocationId": "1-gone"}])
    e = classify_ending(row, EndingIndex.build([row]))
    assert e.ending_class == RE_REGISTRATION and e.successors_in_data == ()


def test_dormant_ending():
    row = _ended(dormancy="Y")
    assert classify_ending(row, EndingIndex.build([row])).ending_class == DORMANT


def test_missing_end_date_is_unresolved():
    row = _ended(deregistrationDate=None)
    assert classify_ending(row, EndingIndex.build([row])).ending_class == UNRESOLVED


def test_unlinked_lookalike_successor_is_unresolved_not_a_closure():
    e = classify_ending(_ended(), EndingIndex.build([_ended(), _live(name="ROSE COURT", postalCode="ab12cd")]))
    assert (e.ending_class, e.successor_ids) == (UNRESOLVED, ("1-new",))


def test_lookalike_outside_window_does_not_block_closure():
    far = _live(registrationDate="2020-01-01")
    assert classify_ending(_ended(), EndingIndex.build([_ended(), far])).ending_class == CONFIRMED_CLOSURE


def test_classifier_for_export_returns_class_names():
    rows = [_ended(), _live(lid="1-x", name="Other")]
    classify = classifier_for_export(rows)
    assert [classify(r) for r in rows] == [CONFIRMED_CLOSURE, "not_ended"]
