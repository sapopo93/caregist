-- Reverses 071_territory_brief_buyer_scope.sql. For controlled non-production
-- verification only (db/migrations/README.md): it discards every stored buyer
-- scope and exclusion list. Production recovery is a forward-fix migration or a
-- Neon point-in-time restore, not this file.
DROP TRIGGER IF EXISTS territory_brief_scope_versions_frozen ON territory_brief_scope_versions;
DROP FUNCTION IF EXISTS prevent_territory_brief_scope_mutation();
DROP TABLE IF EXISTS territory_brief_scope_exclusions;
DROP TABLE IF EXISTS territory_brief_scope_versions;
