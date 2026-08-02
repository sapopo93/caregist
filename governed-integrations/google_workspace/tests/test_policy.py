from pathlib import Path
import sys

MODULE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE_DIR))

from policy import (
    DOCUMENT_OAUTH_SCOPES,
    GMAIL_OAUTH_SCOPES,
    ForbiddenOperation,
    WorkspacePolicy,
    assert_email_action_allowed,
)


def test_gmail_and_document_scopes_are_separate_least_privilege_grants():
    assert GMAIL_OAUTH_SCOPES == ("https://www.googleapis.com/auth/gmail.readonly",)
    assert DOCUMENT_OAUTH_SCOPES == ("https://www.googleapis.com/auth/drive.file",)
    assert set(GMAIL_OAUTH_SCOPES).isdisjoint(DOCUMENT_OAUTH_SCOPES)


def test_read_only_gmail_actions_are_allowed():
    for action in ("search", "get", "labels"):
        assert_email_action_allowed(action)


def test_every_gmail_write_or_mutation_action_is_denied():
    for action in ("send", "reply", "draft", "modify", "delete", "trash", "label"):
        try:
            assert_email_action_allowed(action)
        except ForbiddenOperation:
            continue
        raise AssertionError(f"Gmail action unexpectedly allowed: {action}")


def test_unknown_gmail_action_fails_closed():
    try:
        assert_email_action_allowed("future-new-action")
    except ForbiddenOperation:
        return
    raise AssertionError("Unknown Gmail action must fail closed")


def _metadata_fixture():
    return {
        "assigned-root": {"id": "assigned-root", "parents": []},
        "nested-folder": {"id": "nested-folder", "parents": ["assigned-root"]},
        "doc-inside": {"id": "doc-inside", "parents": ["nested-folder"]},
        "sheet-inside": {"id": "sheet-inside", "parents": ["assigned-root"]},
        "slide-inside": {"id": "slide-inside", "parents": ["assigned-root"]},
        "outside-root": {"id": "outside-root", "parents": []},
        "doc-outside": {"id": "doc-outside", "parents": ["outside-root"]},
        "cycle-a": {"id": "cycle-a", "parents": ["cycle-b"]},
        "cycle-b": {"id": "cycle-b", "parents": ["cycle-a"]},
    }


def _getter(file_id):
    return _metadata_fixture().get(file_id)


def test_docs_sheets_and_slides_inside_assigned_folder_are_allowed():
    policy = WorkspacePolicy(allowed_folder_ids=frozenset({"assigned-root"}))
    policy.assert_file_action_allowed("docs", "update", "doc-inside", _getter)
    policy.assert_file_action_allowed("sheets", "append", "sheet-inside", _getter)
    policy.assert_file_action_allowed("slides", "update", "slide-inside", _getter)


def test_document_outside_assigned_folder_is_denied():
    policy = WorkspacePolicy(allowed_folder_ids=frozenset({"assigned-root"}))
    try:
        policy.assert_file_action_allowed("docs", "get", "doc-outside", _getter)
    except ForbiddenOperation:
        return
    raise AssertionError("Out-of-folder document must be denied")


def test_new_file_parent_must_be_inside_assigned_folder():
    policy = WorkspacePolicy(allowed_folder_ids=frozenset({"assigned-root"}))
    policy.assert_create_target_allowed("slides", "nested-folder", _getter)
    try:
        policy.assert_create_target_allowed("sheets", "outside-root", _getter)
    except ForbiddenOperation:
        return
    raise AssertionError("Creation outside assigned folders must be denied")


def test_missing_metadata_and_parent_cycles_fail_closed():
    policy = WorkspacePolicy(allowed_folder_ids=frozenset({"assigned-root"}))
    for file_id in ("missing", "cycle-a"):
        try:
            policy.assert_file_action_allowed("drive", "get", file_id, _getter)
        except ForbiddenOperation:
            continue
        raise AssertionError(f"Unsafe metadata path unexpectedly allowed: {file_id}")


def test_unknown_service_or_file_action_fails_closed():
    policy = WorkspacePolicy(allowed_folder_ids=frozenset({"assigned-root"}))
    for service, action in (("calendar", "get"), ("docs", "delete"), ("slides", "share")):
        try:
            policy.assert_file_action_allowed(service, action, "doc-inside", _getter)
        except ForbiddenOperation:
            continue
        raise AssertionError(f"Unexpectedly allowed: {service}.{action}")


def test_notebooklm_allows_public_urls_and_sanitised_research_folder_files():
    policy = WorkspacePolicy(
        allowed_folder_ids=frozenset({"assigned-root"}),
        notebook_source_folder_ids=frozenset({"nested-folder"}),
    )
    policy.assert_notebook_source_allowed("public_url", "public")
    policy.assert_notebook_source_allowed("drive_file", "sanitised", file_id="doc-inside", get_metadata=_getter)


def test_notebooklm_never_accepts_gmail_as_a_source():
    policy = WorkspacePolicy(
        allowed_folder_ids=frozenset({"assigned-root"}),
        notebook_source_folder_ids=frozenset({"nested-folder"}),
    )
    try:
        policy.assert_notebook_source_allowed("gmail", "public")
    except ForbiddenOperation:
        return
    raise AssertionError("Gmail must never be an authorised NotebookLM source")


def test_notebooklm_rejects_personal_confidential_and_regulated_classes():
    policy = WorkspacePolicy(
        allowed_folder_ids=frozenset({"assigned-root"}),
        notebook_source_folder_ids=frozenset({"nested-folder"}),
    )
    for classification in ("personal", "confidential", "regulated", "secret"):
        try:
            policy.assert_notebook_source_allowed("public_url", classification)
        except ForbiddenOperation:
            continue
        raise AssertionError(f"NotebookLM classification unexpectedly allowed: {classification}")


def test_notebooklm_drive_source_must_be_in_dedicated_research_folder():
    policy = WorkspacePolicy(
        allowed_folder_ids=frozenset({"assigned-root"}),
        notebook_source_folder_ids=frozenset({"nested-folder"}),
    )
    try:
        policy.assert_notebook_source_allowed("drive_file", "sanitised", file_id="sheet-inside", get_metadata=_getter)
    except ForbiddenOperation:
        return
    raise AssertionError("A general assigned-folder file must not enter NotebookLM")
