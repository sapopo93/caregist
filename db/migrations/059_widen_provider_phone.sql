-- Stop uncontrolled upstream data from halting the reconciliation pipeline.
--
-- care_providers.phone stores CQC's `mainPhoneNumber` verbatim. That is a
-- free-text field in a public dataset we do not control, so its width is not
-- ours to assume. On 2026-09-03 location 1-29250185054 was published with
-- '0794989994707949899947' -- an operator had typed 07949899947 twice, 22
-- characters into VARCHAR(20). The insert raised
-- "value too long for type character varying(20)", which killed shard 1 of
-- reconciliation batch 7fac8994 at offset 4787. Seven of eight shards had
-- completed; the batch could never finalize, so no CQC freshness watermark was
-- written, so commercialReadiness.checkoutReady stayed false and the public
-- pricing page rendered "Paid checkout unavailable" for a month.
--
-- One malformed phone number in someone else's dataset stopped all revenue.
-- Widening is the correct fix: this column mirrors a foreign free-text field,
-- and PostgreSQL widens a varchar in place without rewriting the table.
-- clean_location() also clamps the value, so the two changes are belt and
-- braces rather than alternatives.

ALTER TABLE care_providers ALTER COLUMN phone TYPE VARCHAR(50);

COMMENT ON COLUMN care_providers.phone IS
  'CQC mainPhoneNumber, stored verbatim. Upstream free text: never assume a width, a format, or that it is dialable. Normalised numbers belong in the CRM (crm_contacts.phone_e164), which is E.164-checked.';
