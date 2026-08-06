from tools.evidence_language_guard import scan_text, scan_paths


def test_scan_text_rejects_banned_provider_label():
    findings = scan_text("digest.html", "New failing provider detected in London.")

    assert len(findings) == 1
    assert findings[0].phrase == "failing provider"
    assert findings[0].path == "digest.html"


def test_scan_text_accepts_evidence_grade_framing():
    findings = scan_text(
        "report.html",
        "This location has stale public rating visibility and elevated inspection age.",
    )

    assert findings == []


def test_scan_paths_ignores_non_output_csp_terms(tmp_path):
    output_file = tmp_path / "digest.html"
    output_file.write_text("A poor provider label should not ship.", encoding="utf-8")
    code_file = tmp_path / "middleware.ts"
    code_file.write_text("const csp = \"style-src 'unsafe-inline'\";", encoding="utf-8")

    findings = scan_paths([tmp_path])

    assert [(finding.path, finding.phrase) for finding in findings] == [
        (str(output_file), "poor provider")
    ]
