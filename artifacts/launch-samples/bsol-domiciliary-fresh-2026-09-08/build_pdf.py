import json
from pathlib import Path
from html import escape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from pypdf import PdfReader

here = Path(__file__).resolve().parent
data = json.loads((here / 'pack-data.json').read_text())
out = here.parents[2] / 'output/pdf/caregist-birmingham-solihull-executive-brief.pdf'
out.parent.mkdir(parents=True, exist_ok=True)
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='TitleCG', fontName='Helvetica-Bold', fontSize=25, leading=29, textColor=HexColor('#193447'), spaceAfter=20))
styles['Heading2'].textColor = HexColor('#193447')
styles['BodyText'].fontSize = 10.5
styles['BodyText'].leading = 15
styles['BodyText'].spaceAfter = 10
story = []
def p(text, style='BodyText'):
    story.append(Paragraph(text, styles[style]))
def title(text):
    p(text, 'TitleCG')
def example(row):
    p(escape(row['provider_name']), 'Heading2')
    p('<b>Published fact:</b> ' + escape(row['published_fact']))
    p('<b>Research action:</b> ' + escape(row['reason_for_review']))
    p('<b>Ask:</b> ' + escape(row['qualification_question']))
    p('<link href="' + row['cqc_url'] + '" color="#176481">CQC location ' + row['location_id'] + '</link>')

title('Birmingham &amp; Solihull\n<br/>Territory account review')
p('CareGist | 8 September 2026 | Review copy')
p('For a homecare recruitment or staffing business planning account research. The selection criteria are illustrative and still need agreement with the buyer.')
p('353 locations. 329 provider organisations.', 'Heading2')
p('The 1 September CQC edition contains 297 qualifying locations in Birmingham and 56 in Solihull. All 353 location and provider IDs match the 2 September directory. These are non-dormant locations marked for domiciliary care in the monthly source.')
p('25 organisations, two research routes', 'Heading2')
p('The shortlist includes all 15 providers with more than one qualifying local location, followed by 10 other providers selected by their most recent location registration date. This is a transparent review order, not a score for hiring demand.')
p('Start with the workbook Shortlist tab. Use the published fact, research action and qualification question together. Use the Locations tab to see the other branches under the same provider ID.')
p('Service mix affects account fit', 'Heading2')
p('182 locations also carry the supported-living service flag. Categories overlap. A buyer serving homecare alone should check whether its service also fits the provider\'s supported-living activity.')
p('What this evidence establishes', 'Heading2')
p('A dated account universe, provider-to-location grouping and public registration facts. It does not establish vacancies, staffing shortages, supplier budgets, buying intent or a likely sales return. Source publication and registration dates are not proof of current operations.')
story.append(PageBreak())
title('Route 1: coordinate local accounts')
p('15 shortlisted providers have several qualifying locations. Review them at provider level before assigning separate branch research. A shared CQC provider ID is the grouping key, not an assertion about ultimate corporate ownership.')
for row in data['shortlist'][:3]:
    example(row)
p('Use the workbook to filter all locations for each provider ID. The England counts use the same non-dormant domiciliary filter in the monthly source. They do not count every business owned by the group.')
story.append(PageBreak())
title('Route 2: review recent registrations')
p('The next 10 organisations are outside the multi-location set. Their most recent qualifying location registration dates determine review order. Registration is a reason to check account fit, not evidence of a new contract or a recruitment need.')
for row in data['shortlist'][15:18]:
    example(row)
p('Before treating any account as relevant, establish current service delivery, who chooses suppliers and whether external staffing fits the service. No outreach or qualification interview was conducted for this pack.')
story.append(PageBreak())
title('Use and evidence notes')
p('Work from the IDs', 'Heading2')
p('The workbook contains 353 location rows and 25 distinct shortlisted provider IDs. Location ID identifies a service location. Provider ID joins the shortlist to its local locations. CSV files accompany the workbook. Mapping these columns to a buyer\'s CRM remains a separate import step.')
p('Keep missing ratings distinct', 'Heading2')
p('The source contains 162 Good, 43 Requires improvement, 2 Outstanding and 1 Inadequate ratings. Another 19 are explicitly Not Rated and 126 have no supplied rating. An absent rating is not a finding of Not Yet Inspected. Rating publication dates do not by themselves prove rating movements.')
p('Checks completed on 8 September', 'Heading2')
p('Downloaded the published monthly and weekly files. Selected Birmingham and Solihull rows with the domiciliary flag and non-dormant status. Matched all 353 selected location/provider IDs and authorities against the weekly directory. Opened one representative CQC location page per shortlisted provider: all 25 loaded and matched the location name. This page check does not validate every field or every branch.')
p('Sources and limitations', 'Heading2')
p('<link href="https://www.cqc.org.uk/about-us/transparency/using-cqc-data" color="#176481">CQC: Using CQC data</link>. Monthly active-locations edition: 1 September 2026. Weekly directory edition: 2 September 2026. Retrieved 8 September 2026. Exact download URLs and source row references appear in the workbook and local evidence record.')
p('Published files lag changes. The national source files have different dates and row counts. Reconciliation here covers the 353 selected records only. No closure series, live monitoring or continuous data service is included.')
p('Your next decision', 'Heading2')
p('Confirm territory, service mix, exclusions and the question your team needs to answer. If these criteria differ from the sample, the shortlist must be revised and checked before delivery. Agree CRM columns and a delivery date before ordering.')
p('Contains public sector information licensed under the Open Government Licence v3.0. CareGist is independent of the Care Quality Commission and is not endorsed by it.')

def footer(canvas, doc):
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(HexColor('#536575'))
    canvas.drawString(42, 27, 'CareGist | September 2026 source editions | Review copy')
    canvas.drawRightString(A4[0]-42, 27, str(doc.page))
SimpleDocTemplate(str(out), pagesize=A4, rightMargin=42, leftMargin=42, topMargin=42, bottomMargin=45).build(story, onFirstPage=footer, onLaterPages=footer)
reader = PdfReader(out)
assert len(reader.pages) == 4, len(reader.pages)
assert all(len(page.extract_text()) > 500 for page in reader.pages)
print(f'PDF_PASS: 4 pages; {out}')
