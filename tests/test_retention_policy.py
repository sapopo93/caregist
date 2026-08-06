"""Static and unit-level checks for privacy retention controls."""

from tools.prune_retention import ANONYMISATION_RULES, RETENTION_RULES


def test_declared_retention_rules_cover_all_personal_data_intakes():
    deletion_rules = {rule[0]: rule[2] for rule in RETENTION_RULES}
    anonymisation_rules = {rule[0]: rule for rule in ANONYMISATION_RULES}

    assert deletion_rules["leads"] == 365
    assert deletion_rules["export_access_tokens"] == 90
    assert deletion_rules["analytics_events"] == 90
    assert {"enquiries", "reviews", "provider_claims"} <= anonymisation_rules.keys()


def test_claim_retention_removes_authority_and_moderation_content():
    claim_rule = next(rule for rule in ANONYMISATION_RULES if rule[0] == "provider_claims")
    set_clause = claim_rule[4]

    assert "proof_of_association = '[retention-anonymised]'" in set_clause
    assert "admin_notes = NULL" in set_clause
    assert "claimant_user_id = NULL" in set_clause
