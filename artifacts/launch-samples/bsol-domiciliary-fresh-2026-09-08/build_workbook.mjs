import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '../../..');
const out = path.join(root, 'outputs/01a080c9-7c69-71e0-ab8d-821ce92d1e44');
const preview = path.join(here, 'qa');
await fs.mkdir(out, { recursive: true });
await fs.mkdir(preview, { recursive: true });
const pack = JSON.parse(await fs.readFile(path.join(here, 'pack-data.json'), 'utf8'));
const wb = Workbook.create();
const overview = wb.worksheets.add('Start here');
const shortlist = wb.worksheets.add('Shortlist');
const data = wb.worksheets.add('Locations');
const font = 'Arial', navy = '#183247', pale = '#EEF3F6';

function style(sheet, rows, cols) {
  sheet.showGridLines = false;
  const r = sheet.getRangeByIndexes(0, 0, rows, cols);
  r.format.font = { name: font, size: 10, color: '#203442' };
  r.format.rowHeight = 25;
  r.format.verticalAlignment = 'center';
  r.format.columnWidth = 22;
}
function table(sheet, headers, matrix, name) {
  const n = headers.length, end = matrix.length + 5;
  style(sheet, end + 1, n);
  sheet.getRangeByIndexes(4, 0, 1, n).values = [headers];
  sheet.getRangeByIndexes(5, 0, matrix.length, n).values = matrix;
  const h = sheet.getRangeByIndexes(4, 0, 1, n);
  h.format = { fill: navy, font: { name: font, size: 10, color: '#FFFFFF', bold: true }, wrapText: true, horizontalAlignment: 'center', rowHeight: 36 };
  sheet.tables.add(sheet.getRangeByIndexes(4, 0, matrix.length + 1, n).address, true, name);
  sheet.freezePanes.freezeRows(5);
  sheet.freezePanes.freezeColumns(3);
  for (let row = 5; row < end; row += 2) sheet.getRangeByIndexes(row, 0, 1, n).format.fill = pale;
  return end;
}
function title(sheet, titleText, context) {
  sheet.getRange('A2').values = [[titleText]];
  sheet.getRange('A2').format.font = { name: font, size: 16, bold: true, color: navy };
  sheet.getRange('A3').values = [[context]];
  sheet.getRange('A3').format.font = { name: font, size: 10, italic: true, color: '#526574' };
}
const date = s => s ? new Date(s + 'T00:00:00Z') : null;
const sHeaders = ['Order', 'Review route', 'Provider organisation', 'Local locations', 'Service mix', 'Published fact', 'Reason for review', 'Qualification question', 'Uncertainty', 'CQC evidence', 'Provider ID', 'Location ID', 'Representative location', 'Source edition', 'Page checked', 'Page result'];
const sRows = pack.shortlist.map(r => [r.review_order, r.review_route, r.provider_name, r.local_locations, r.service_mix, r.published_fact, r.reason_for_review, r.qualification_question, r.uncertainty, r.cqc_url, r.provider_id, r.location_id, r.representative_location, date(r.source_edition), date(r.web_check_date), r.web_check_result]);
const sEnd = table(shortlist, sHeaders, sRows, 'AccountShortlist');
title(shortlist, '25 organisations to review', 'Illustrative staffing-buyer criteria. Review order is not a hiring-demand score.');
shortlist.getRange('A5:A30').format.columnWidth = 8;
shortlist.getRange('B5:B30').format.columnWidth = 30;
shortlist.getRange('C5:C30').format.columnWidth = 47;
shortlist.getRange('D5:D30').format.columnWidth = 14;
shortlist.getRange('E5:E30').format.columnWidth = 38;
shortlist.getRange('F5:I30').format.columnWidth = 67;
shortlist.getRange('J5:J30').format.columnWidth = 59;
shortlist.getRange('K5:L30').format.columnWidth = 23;
shortlist.getRange('M5:M30').format.columnWidth = 49;
shortlist.getRange('N5:P30').format.columnWidth = 18;
shortlist.getRange(`A6:P${sEnd}`).format.wrapText = true;
shortlist.getRange(`A6:P${sEnd}`).format.rowHeight = 100;
shortlist.getRange(`N6:O${sEnd}`).setNumberFormat('dd mmm yyyy');
shortlist.getRange(`J6:J${sEnd}`).formulas = pack.shortlist.map(r => [`=HYPERLINK("${r.cqc_url}","${r.location_id}")`]);

const dHeaders = ['Location ID', 'Location name', 'Provider organisation', 'Provider ID', 'Local authority', 'Postcode', 'Registered', 'Rating as published', 'Rating publication', 'Inherited rating', 'Service types', 'Service user bands', 'Supported living', 'England domiciliary locations', 'Territory locations', 'CQC location URL', 'Provider website', 'Monthly edition', 'Weekly cross-check', 'Retrieved', 'Monthly source row'];
const dRows = pack.dataset.map(r => [r.location_id,r.location_name,r.provider_name,r.provider_id,r.local_authority,r.postcode,date(r.registration_date),r.rating_as_published,date(r.rating_publication_date),r.inherited_rating,r.service_types,r.service_user_bands,r.supported_living,r.provider_country_domiciliary_locations,r.provider_territory_locations,r.cqc_url,r.provider_website,date(r.source_edition),date(r.weekly_crosscheck_edition),date(r.source_retrieved_date),r.monthly_source_row]);
const dEnd = table(data, dHeaders, dRows, 'TerritoryLocations');
title(data, 'Birmingham and Solihull domiciliary care', '353 non-dormant locations in the 1 September edition; identity cross-check against 2 September directory.');
data.getRange(`A5:D${dEnd}`).format.columnWidth = 27;
data.getRange(`B5:C${dEnd}`).format.columnWidth = 57;
data.getRange(`E5:F${dEnd}`).format.columnWidth = 20;
data.getRange(`G6:G${dEnd}`).setNumberFormat('dd mmm yyyy');
data.getRange(`I6:I${dEnd}`).setNumberFormat('dd mmm yyyy');
data.getRange(`R6:T${dEnd}`).setNumberFormat('dd mmm yyyy');
data.getRange(`K5:L${dEnd}`).format.columnWidth = 65;
data.getRange(`P5:Q${dEnd}`).format.columnWidth = 65;
data.getRange(`A6:U${dEnd}`).format.wrapText = true;
data.getRange(`A6:U${dEnd}`).format.rowHeight = 64;
data.getRange(`P6:P${dEnd}`).formulas = pack.dataset.map(r => [`=HYPERLINK("${r.cqc_url}","${r.cqc_url}")`]);

style(overview, 36, 8);
overview.tabColor = navy;
title(overview, 'CareGist territory account review', 'Birmingham and Solihull. September 2026 source editions. Review copy.');
overview.getRange('A5:B9').values = [['Territory', 'Locations'],['Birmingham',null],['Solihull',null],['Total',null],['Selected organisations',null]];
overview.getRange('B6').formulas = [[`=COUNTIFS('Locations'!$E$6:$E$${dEnd},A6)`]];
overview.getRange('B7').formulas = [[`=COUNTIFS('Locations'!$E$6:$E$${dEnd},A7)`]];
overview.getRange('B8').formulas = [['=SUM(B6:B7)']];
overview.getRange('B9').formulas = [[`=COUNTA('Shortlist'!$K$6:$K$${sEnd})`]];
overview.getRange('A5:B5').format = { fill: navy, font: { name: font, color: '#FFFFFF', bold: true } };
overview.getRange('A11').values = [['How to use the pack']];
const notes = [
  'Start with Shortlist: 15 providers with several local locations and 10 recent-registration accounts.',
  'The two routes answer different research questions. They are not a prediction of staffing demand.',
  'For multi-location providers, establish whether supplier decisions sit centrally or with branches.',
  'For recent registrations, check current operations and fit before treating the account as relevant.',
  'The illustrative selection criteria still need agreement with the actual buyer.',
  'No named decision-makers or personal contact details are included.',
  'Page checks confirm access and the representative location name, not every field on every branch.',
  'A blank rating remains blank. Not Rated is distinct from an absent field or Not Yet Inspected.',
  'CQC reports delayed file updates. Source edition dates are not live operational verification.',
  'CQC service categories can overlap. Domiciliary care may coexist with supported living.',
];
overview.getRange('A12:A21').values = notes.map(x => [x]);
overview.getRange('A23').values = [['Sources and terms of use']];
overview.getRange('A24:A29').values = [
  ['CQC care directory with filters, edition 1 September 2026; downloaded 8 September 2026.'],
  [pack.metadata.source_manifest[0].url],
  ['CQC weekly care directory, edition 2 September 2026; downloaded 8 September 2026.'],
  [pack.metadata.source_manifest[1].url],
  ['CQC data is reused under the Open Government Licence v3.0. CareGist is independent of CQC.'],
  ['Source rows refer to the HSCA_Active_Locations sheet converted by LibreOffice; header is row 1.'],
];
overview.getRange('A31').values = [['Import guidance']];
overview.getRange('A32:A34').values = [
  ['Use location_id as the location key and provider_id as the provider grouping key.'],
  ['CSV fields are documented in the accompanying schema. Keep identifiers and postcodes as text.'],
  ['No live CRM import is claimed. Map fields to the selected CRM before importing.'],
];
overview.getRange('A5:A9').format.columnWidth = 31;
overview.getRange('B5:B9').format.columnWidth = 16;
for (const a of ['A11','A23','A31']) overview.getRange(a).format.font = {name:font,size:12,bold:true};
overview.getRange('A12:A34').format.wrapText = false;

wb.recalculate();
const expected = [297,56,353,25];
const actual = overview.getRange('B6:B9').values.flat();
if (JSON.stringify(actual) !== JSON.stringify(expected)) throw new Error('Summary mismatch: ' + JSON.stringify(actual));
console.log((await wb.inspect({kind:'table',range:"'Start here'!A5:B9",include:'values,formulas',tableMaxRows:5,tableMaxCols:2})).ndjson);
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#SPILL!',options:{useRegex:true,maxResults:20},summary:'Final error scan'})).ndjson);
for (const [sheetName,range,file] of [
  ['Start here','A1:H21','overview.png'],
  ['Shortlist','A1:E9','shortlist.png'],
  ['Shortlist','F5:I8','reasons.png'],
  ['Locations','A1:G9','locations.png'],
]) {
  const blob = await wb.render({sheetName,range,scale:1.5,format:'png'});
  await fs.writeFile(path.join(preview,file),new Uint8Array(await blob.arrayBuffer()));
}
await (await SpreadsheetFile.exportXlsx(wb)).save(path.join(out,'caregist-birmingham-solihull-territory-brief.xlsx'));
// Artifact-tool does not calculate HYPERLINK. Recalculate with LibreOffice
// before release; verify_pack.py rejects every saved Excel error cell.
const recalculated = path.join(preview,'recalculated');
await fs.mkdir(recalculated,{recursive:true});
execFileSync('/opt/homebrew/bin/soffice',['-env:UserInstallation=file:///tmp/caregist-20260908-xlsx-qa','--headless','--convert-to','xlsx','--outdir',recalculated,path.join(out,'caregist-birmingham-solihull-territory-brief.xlsx')]);
await fs.copyFile(path.join(recalculated,'caregist-birmingham-solihull-territory-brief.xlsx'),path.join(out,'caregist-birmingham-solihull-territory-brief.xlsx'));
await fs.copyFile(path.join(here,'territory-dataset.csv'),path.join(out,'territory-dataset.csv'));
await fs.copyFile(path.join(here,'shortlist-25.csv'),path.join(out,'shortlist-25.csv'));
console.log('WORKBOOK_EXPORTED',out);
