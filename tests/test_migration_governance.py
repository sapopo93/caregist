from tools.check_migration_governance import check_governance


def test_governance_rejects_prisma_db_push(tmp_path):
    (tmp_path / "script.sh").write_text("prisma db push\n", encoding="utf-8")

    findings = check_governance(tmp_path)

    assert any(f.rule == "no_prisma_db_push" for f in findings)


def test_governance_rejects_destructive_migration_without_approval(tmp_path, monkeypatch):
    migrations = tmp_path / "db" / "migrations"
    migrations.mkdir(parents=True)
    (migrations / "036_bad.sql").write_text("ALTER TABLE users DROP COLUMN name;\n", encoding="utf-8")
    down = migrations / "down"
    down.mkdir()
    (down / "036_bad.down.sql").write_text("ALTER TABLE users ADD COLUMN name text;\n", encoding="utf-8")
    monkeypatch.delenv("APPROVED_DESTRUCTIVE", raising=False)

    findings = check_governance(tmp_path)

    assert any(f.rule == "destructive_sql_requires_approval" for f in findings)


def test_governance_accepts_only_the_frozen_047_destructive_migration(tmp_path, monkeypatch):
    migrations = tmp_path / "db" / "migrations"
    migrations.mkdir(parents=True)
    (migrations / "047_expand_analytics_provider_reference.sql").write_text(
        "ALTER TABLE analytics_events ALTER COLUMN provider_id TYPE TEXT;\n",
        encoding="utf-8",
    )
    down = migrations / "down"
    down.mkdir()
    (down / "047_expand_analytics_provider_reference.down.sql").write_text(
        "ALTER TABLE analytics_events ALTER COLUMN provider_id TYPE VARCHAR(20);\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("APPROVED_DESTRUCTIVE", raising=False)

    assert check_governance(tmp_path) == []


def test_governance_requires_down_migration_for_numbered_sql(tmp_path):
    migrations = tmp_path / "db" / "migrations"
    migrations.mkdir(parents=True)
    (migrations / "036_additive.sql").write_text("CREATE TABLE demo (id bigint);\n", encoding="utf-8")

    findings = check_governance(tmp_path)

    assert any(f.rule == "missing_down_migration" for f in findings)


def test_governance_accepts_additive_reversible_migration(tmp_path):
    migrations = tmp_path / "db" / "migrations"
    migrations.mkdir(parents=True)
    (migrations / "036_additive.sql").write_text("CREATE TABLE demo (id bigint);\n", encoding="utf-8")
    down = migrations / "down"
    down.mkdir()
    (down / "036_additive.down.sql").write_text("DROP TABLE IF EXISTS demo;\n", encoding="utf-8")

    assert check_governance(tmp_path) == []


def test_governance_rejects_duplicate_migration_numbers(tmp_path):
    migrations = tmp_path / "db" / "migrations"
    migrations.mkdir(parents=True)
    (migrations / "036_first.sql").write_text("CREATE TABLE first_demo (id bigint);\n", encoding="utf-8")
    (migrations / "036_second.sql").write_text("CREATE TABLE second_demo (id bigint);\n", encoding="utf-8")
    down = migrations / "down"
    down.mkdir()
    (down / "036_first.down.sql").write_text("DROP TABLE IF EXISTS first_demo;\n", encoding="utf-8")
    (down / "036_second.down.sql").write_text("DROP TABLE IF EXISTS second_demo;\n", encoding="utf-8")

    findings = check_governance(tmp_path)

    assert any(f.rule == "duplicate_migration_number" for f in findings)
