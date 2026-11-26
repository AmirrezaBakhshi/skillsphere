from __future__ import annotations

from dataclasses import dataclass, field
from typing import BinaryIO
from uuid import UUID

from apps.projects.domain.entities import ProjectEntity
from apps.projects.domain.exceptions import InvalidFileError, ProjectNotFoundError
from apps.projects.domain.ports import ProjectRepository

DEFAULT_ALLOWED_CONTENT_TYPES = (
    "application/pdf",
    "application/zip",
    "application/x-zip-compressed",
    "image/png",
    "image/jpeg",
)
DEFAULT_MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB

# Validate file signatures instead of trusting the client-controlled multipart
# Content-Type header. This is format identification, not malware scanning.
_FILE_SIGNATURES = {
    "application/pdf": lambda header: header.startswith(b"%PDF-"),
    "application/zip": lambda header: header.startswith((b"PK\\x03\\x04", b"PK\\x05\\x06", b"PK\\x07\\x08")),
    "application/x-zip-compressed": lambda header: header.startswith((b"PK\\x03\\x04", b"PK\\x05\\x06", b"PK\\x07\\x08")),
    "image/png": lambda header: header.startswith(b"\\x89PNG\\r\\n\\x1a\\n"),
    "image/jpeg": lambda header: header.startswith(b"\\xff\\xd8\\xff"),
}


def _matches_declared_content_type(file: BinaryIO, content_type: str) -> bool:
    signature_check = _FILE_SIGNATURES.get(content_type)
    if signature_check is None:
        return False

    try:
        file.seek(0)
        header = file.read(8)
    finally:
        file.seek(0)

    return signature_check(header)



@dataclass
class UploadProjectService:
    """
    Use case: validate and persist a new project upload. Validation rules
    (max size, allowed types) are injected rather than imported from
    Django settings directly, so this class stays framework-agnostic and
    trivially unit-testable with different limits.
    """

    repository: ProjectRepository
    max_file_size_bytes: int = DEFAULT_MAX_FILE_SIZE_BYTES
    allowed_content_types: tuple[str, ...] = field(default_factory=lambda: DEFAULT_ALLOWED_CONTENT_TYPES)

    def upload(
        self,
        *,
        owner_id: UUID,
        title: str,
        description: str,
        file: BinaryIO,
        file_name: str,
        file_size: int,
        content_type: str,
        tags: list[str] = (),
    ) -> ProjectEntity:
        if file_size > self.max_file_size_bytes:
            raise InvalidFileError(
                f"File is {file_size} bytes, which exceeds the {self.max_file_size_bytes} byte limit"
            )
        if content_type not in self.allowed_content_types:
            raise InvalidFileError(f"Content type '{content_type}' is not allowed")
        if not _matches_declared_content_type(file, content_type):
            raise InvalidFileError(
                f"File content does not match the declared content type '{content_type}'"
            )

        return self.repository.create(
            owner_id=owner_id,
            title=title,
            description=description,
            file=file,
            file_name=file_name,
            file_size=file_size,
            content_type=content_type,
            tags=tags,
        )


@dataclass
class ListMyProjectsService:
    repository: ProjectRepository

    def list_for_owner(self, owner_id: UUID) -> list[ProjectEntity]:
        return self.repository.list_for_owner(owner_id)


@dataclass
class GetProjectForDownloadService:
    """Use case: fetch a project's file path, only if the requester owns it."""

    repository: ProjectRepository

    def get_file_path(self, *, project_id: UUID, owner_id: UUID) -> str:
        project = self.repository.get_for_owner(project_id=project_id, owner_id=owner_id)
        if project is None:
            raise ProjectNotFoundError(f"No project {project_id} for this user")
        path = self.repository.get_file_path(project_id)
        if path is None:
            raise ProjectNotFoundError("Project file is missing")
        return path
