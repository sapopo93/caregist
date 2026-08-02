"""Fail-closed policy for the governed Google Workspace integration.

This module contains no credentials and performs no network operations.
"""

from dataclasses import dataclass
from typing import Callable, Mapping, Optional


class PolicyViolation(RuntimeError):
    """Base class for a denied Workspace operation."""


class ForbiddenOperation(PolicyViolation):
    """Raised when an operation is outside the founder-approved capability set."""


GMAIL_OAUTH_SCOPES = (
    "https://www.googleapis.com/auth/gmail.readonly",
)

DOCUMENT_OAUTH_SCOPES = (
    "https://www.googleapis.com/auth/drive.file",
)

_ALLOWED_EMAIL_ACTIONS = frozenset({"search", "get", "labels"})
_ALLOWED_FILE_ACTIONS = {
    "drive": frozenset({"get", "search", "upload", "download", "create-folder", "update"}),
    "docs": frozenset({"get", "create", "append", "update"}),
    "sheets": frozenset({"get", "create", "append", "update"}),
    "slides": frozenset({"get", "create", "update"}),
}

Metadata = Mapping[str, object]
MetadataGetter = Callable[[str], Optional[Metadata]]


def assert_email_action_allowed(action: str) -> None:
    """Allow only non-mutating Gmail operations; deny unknown actions."""
    if action not in _ALLOWED_EMAIL_ACTIONS:
        raise ForbiddenOperation(f"Gmail action is not authorised: {action}")


@dataclass(frozen=True)
class WorkspacePolicy:
    """Founder-approved file boundary enforced independently of OAuth."""

    allowed_folder_ids: frozenset[str]
    notebook_source_folder_ids: frozenset[str] = frozenset()
    max_ancestry_nodes: int = 128

    def __post_init__(self) -> None:
        if not self.allowed_folder_ids:
            raise ForbiddenOperation("At least one assigned folder ID is required")

    def _assert_service_action(self, service: str, action: str) -> None:
        allowed = _ALLOWED_FILE_ACTIONS.get(service)
        if allowed is None or action not in allowed:
            raise ForbiddenOperation(f"Workspace action is not authorised: {service}.{action}")

    def _is_within_folder_set(
        self,
        file_id: str,
        allowed_folder_ids: frozenset[str],
        get_metadata: MetadataGetter,
    ) -> bool:
        queue = [file_id]
        visited: set[str] = set()
        while queue:
            current = queue.pop(0)
            if current in allowed_folder_ids:
                return True
            if current in visited:
                raise ForbiddenOperation("Drive ancestry contains a cycle")
            visited.add(current)
            if len(visited) > self.max_ancestry_nodes:
                raise ForbiddenOperation("Drive ancestry exceeds the policy traversal limit")
            metadata = get_metadata(current)
            if not metadata or metadata.get("trashed") is True:
                raise ForbiddenOperation(f"Drive metadata unavailable or unsafe for: {current}")
            parents = metadata.get("parents", [])
            if not isinstance(parents, (list, tuple)):
                raise ForbiddenOperation(f"Invalid Drive parents metadata for: {current}")
            queue.extend(str(parent) for parent in parents if parent)
        return False

    def assert_file_action_allowed(self, service: str, action: str, file_id: str, get_metadata: MetadataGetter) -> None:
        self._assert_service_action(service, action)
        if not self._is_within_folder_set(file_id, self.allowed_folder_ids, get_metadata):
            raise ForbiddenOperation(f"File is outside assigned folders: {file_id}")

    def assert_create_target_allowed(self, service: str, parent_folder_id: str, get_metadata: MetadataGetter) -> None:
        self._assert_service_action(service, "create")
        if not self._is_within_folder_set(parent_folder_id, self.allowed_folder_ids, get_metadata):
            raise ForbiddenOperation(f"Parent is outside assigned folders: {parent_folder_id}")

    def assert_notebook_source_allowed(
        self,
        source_type: str,
        classification: str,
        *,
        file_id: str | None = None,
        get_metadata: MetadataGetter | None = None,
    ) -> None:
        if classification not in {"public", "sanitised"}:
            raise ForbiddenOperation(f"NotebookLM data class is not authorised: {classification}")
        if source_type == "public_url":
            return
        if source_type != "drive_file":
            raise ForbiddenOperation(f"NotebookLM source type is not authorised: {source_type}")
        if not file_id or get_metadata is None or not self.notebook_source_folder_ids:
            raise ForbiddenOperation("NotebookLM Drive source is missing its restricted-folder evidence")
        if not self._is_within_folder_set(file_id, self.notebook_source_folder_ids, get_metadata):
            raise ForbiddenOperation(f"Drive file is outside NotebookLM research folders: {file_id}")
