from pathlib import Path
import sys

import pytest

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
    folder = "application/vnd.google-apps.folder"
    return {
        "assigned-root": {
            "id": "assigned-root",
            "parents": [],
            "trashed": False,
            "mimeType": folder,
        },
        "nested-folder": {
            "id": "nested-folder",
            "parents": ["assigned-root"],
            "trashed": False,
            "mimeType": folder,
        },
        "doc-inside": {
            "id": "doc-inside",
            "parents": ["nested-folder"],
            "trashed": False,
            "mimeType": "application/vnd.google-apps.document",
        },
        "sheet-inside": {
            "id": "sheet-inside",
            "parents": ["assigned-root"],
            "trashed": False,
            "mimeType": "application/vnd.google-apps.spreadsheet",
        },
        "slide-inside": {
            "id": "slide-inside",
            "parents": ["assigned-root"],
            "trashed": False,
            "mimeType": "application/vnd.google-apps.presentation",
        },
        "outside-root": {
            "id": "outside-root",
            "parents": [],
            "trashed": False,
            "mimeType": folder,
        },
        "doc-outside": {
            "id": "doc-outside",
            "parents": ["outside-root"],
            "trashed": False,
            "mimeType": "application/vnd.google-apps.document",
        },
        "cycle-a": {"id": "cycle-a", "parents": ["cycle-b"], "trashed": False, "mimeType": folder},
        "cycle-b": {"id": "cycle-b", "parents": ["cycle-a"], "trashed": False, "mimeType": folder},
        "trashed-folder": {
            "id": "trashed-folder",
            "parents": ["assigned-root"],
            "trashed": True,
            "mimeType": folder,
        },
        "unknown-trash-state": {
            "id": "unknown-trash-state",
            "parents": ["assigned-root"],
            "mimeType": folder,
        },
        "invalid-parents": {
            "id": "invalid-parents",
            "parents": "assigned-root",
            "trashed": False,
            "mimeType": folder,
        },
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


@pytest.mark.parametrize(
    ("service", "action"),
    (
        ("drive", "upload"),
        ("drive", "create-folder"),
        ("docs", "create"),
        ("sheets", "create"),
        ("slides", "create"),
    ),
)
def test_every_authorised_creation_action_accepts_a_valid_parent(service, action):
    policy = WorkspacePolicy(allowed_folder_ids=frozenset({"assigned-root"}))
    policy.assert_create_target_allowed(service, action, "nested-folder", _getter)


@pytest.mark.parametrize(
    ("service", "action"),
    (
        ("drive", "create"),
        ("drive", "update"),
        ("docs", "upload"),
        ("sheets", "append"),
        ("slides", "share"),
        ("calendar", "create"),
        ("docs", "future-new-action"),
    ),
)
def test_wrong_or_unknown_creation_actions_fail_closed(service, action):
    policy = WorkspacePolicy(allowed_folder_ids=frozenset({"assigned-root"}))
    with pytest.raises(ForbiddenOperation):
        policy.assert_create_target_allowed(service, action, "nested-folder", _getter)


def test_creation_outside_assigned_folders_is_denied():
    policy = WorkspacePolicy(allowed_folder_ids=frozenset({"assigned-root"}))
    with pytest.raises(ForbiddenOperation, match="outside assigned folders"):
        policy.assert_create_target_allowed("sheets", "create", "outside-root", _getter)


def test_allowlisted_parent_metadata_is_still_required_and_validated():
    policy = WorkspacePolicy(allowed_folder_ids=frozenset({"assigned-root"}))

    with pytest.raises(ForbiddenOperation, match="metadata unavailable"):
        policy.assert_create_target_allowed("docs", "create", "assigned-root", lambda _file_id: None)

    bad_root = dict(_metadata_fixture()["assigned-root"])
    bad_root["mimeType"] = "application/vnd.google-apps.document"
    with pytest.raises(ForbiddenOperation, match="not a folder"):
        policy.assert_create_target_allowed("docs", "create", "assigned-root", lambda _file_id: bad_root)

    trashed_root = dict(_metadata_fixture()["assigned-root"])
    trashed_root["trashed"] = True
    with pytest.raises(ForbiddenOperation, match="trashed or has unknown state"):
        policy.assert_create_target_allowed("docs", "create", "assigned-root", lambda _file_id: trashed_root)


@pytest.mark.parametrize("parent_id", ("doc-inside", "trashed-folder", "unknown-trash-state"))
def test_non_folder_trashed_or_unknown_state_creation_parents_are_denied(parent_id):
    policy = WorkspacePolicy(allowed_folder_ids=frozenset({"assigned-root"}))
    with pytest.raises(ForbiddenOperation):
        policy.assert_create_target_allowed("drive", "upload", parent_id, _getter)


def test_missing_or_invalid_creation_ancestry_metadata_fails_closed():
    policy = WorkspacePolicy(allowed_folder_ids=frozenset({"assigned-root"}))
    folder = "application/vnd.google-apps.folder"
    missing_parent = {
        "child": {"parents": ["missing"], "trashed": False, "mimeType": folder},
    }
    with pytest.raises(ForbiddenOperation, match="metadata unavailable"):
        policy.assert_create_target_allowed("docs", "create", "child", missing_parent.get)
    with pytest.raises(ForbiddenOperation, match="parents metadata"):
        policy.assert_create_target_allowed("docs", "create", "invalid-parents", _getter)


def test_creation_parent_cycles_and_traversal_limit_fail_closed():
    policy = WorkspacePolicy(allowed_folder_ids=frozenset({"assigned-root"}))
    with pytest.raises(ForbiddenOperation, match="cycle"):
        policy.assert_create_target_allowed("slides", "create", "cycle-a", _getter)

    constrained_policy = WorkspacePolicy(
        allowed_folder_ids=frozenset({"assigned-root"}),
        max_ancestry_nodes=1,
    )
    with pytest.raises(ForbiddenOperation, match="traversal limit"):
        constrained_policy.assert_create_target_allowed("slides", "create", "nested-folder", _getter)


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
