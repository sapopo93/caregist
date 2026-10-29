import assert from 'node:assert/strict';
import test from 'node:test';
import { territoryRatingCoverageSql } from './territory-rating-coverage.ts';

test('Brief rating scope is pinned to the resolved contract and excludes uncertainty', () => {
  const sql = territoryRatingCoverageSql('inadequate');
  assert.match(sql, /territory_brief_source_locations/);
  assert.match(sql, /contract_version/);
  assert.match(sql, /r->>'status' = 'current'/);
  assert.match(sql, /r->>'value' = 'Inadequate'/);
  assert.doesNotMatch(sql, /care_providers/);
  assert.match(territoryRatingCoverageSql('not_yet_inspected'), /r->>'status' = 'unrated'/);
  assert.throws(() => territoryRatingCoverageSql('invalid'));
});
