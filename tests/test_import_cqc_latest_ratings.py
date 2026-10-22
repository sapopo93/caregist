import zipfile

from tools.import_cqc_latest_ratings import overall_ratings

HEADER = ["Location ID", "Service / Population Group", "Domain", "Latest Rating", "Publication Date"]


def _ods(path, rows):
    def cell(v):
        return f'<table:table-cell><text:p>{v}</text:p></table:table-cell>'
    body = "".join(f"<table:table-row>{''.join(cell(c) for c in r)}</table:table-row>" for r in [HEADER, *rows])
    xml = (
        '<office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
        'xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" '
        'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"><office:body><office:spreadsheet>'
        f'<table:table table:name="Locations">{body}</table:table></office:spreadsheet></office:body>'
        "</office:document-content>"
    )
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("content.xml", xml)


def test_only_published_overall_rows_and_ambiguity_skipped(tmp_path):
    p = tmp_path / "r.ods"
    _ods(p, [
        ["1-A", "Overall", "Overall", "Inadequate", "01/09/2026"],
        ["1-A", "Residential", "Safe", "Good", "01/09/2026"],
        ["1-B", "Overall", "Overall", "Not Rated", "01/09/2026"],
        ["1-C", "Overall", "Overall", "Good", "01/09/2026"],
        ["1-C", "Overall", "Overall", "Inadequate", "01/09/2026"],
    ])
    ratings, ambiguous = overall_ratings(p)
    assert ratings == {"1-A": ("Inadequate", "01/09/2026")}
    assert ambiguous == {"1-C"}
