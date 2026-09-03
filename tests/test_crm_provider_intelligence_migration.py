from pathlib import Path


MIGRATION = Path("db/migrations/058_crm_provider_intelligence.sql").read_text()


def test_agent_path_is_proposal_only_and_human_reviewed():
    assert "crm_enrichment_proposals" in MIGRATION
    assert "status = 'pending_review'" in MIGRATION
    assert "reviewed_by_user_id IS NULL" in MIGRATION
    assert "crm_proposals_intelligence_insert" in MIGRATION
    assert "FOR UPDATE" not in MIGRATION.split("crm_proposals_intelligence_insert", 1)[1]


def test_required_business_relationships_are_first_class():
    for table in (
        "crm_referrals",
        "crm_placements",
        "crm_contracts",
        "crm_commissions",
        "crm_evidence",
        "crm_alerts",
    ):
        assert f"CREATE TABLE {table}" in MIGRATION


def test_evidence_states_and_verified_check_are_enforced():
    for state in (
        "verified",
        "strong_source_backed_observation",
        "inferred",
        "conflicting",
        "weak_unverified",
        "requires_human_review",
    ):
        assert f"'{state}'" in MIGRATION
    assert "evidence_state <> 'verified' OR independent_check IS NOT NULL" in MIGRATION


def test_all_new_tables_force_row_level_security():
    assert "ALTER TABLE %I FORCE ROW LEVEL SECURITY" in MIGRATION
    assert "caregist_is_organization_member(organization_id)" in MIGRATION
