-- Non-production reversal only. Removes pinned source references and evidence.
ALTER TABLE territory_brief_orders DROP COLUMN source_edition_id;
DROP TABLE territory_brief_source_locations;
DROP TABLE territory_brief_source_editions;
DROP FUNCTION territory_brief_source_insert_guard();
DROP FUNCTION territory_brief_source_immutable();
