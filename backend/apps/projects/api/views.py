from django.conf import settings
from django.http import FileResponse
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notifications.tasks import create_notification_task
from apps.projects.api.serializers import ProjectSerializer, ProjectUploadSerializer
from apps.projects.application.services import (
    GetProjectForDownloadService,
    ListMyProjectsService,
    UploadProjectService,
)
from apps.projects.infrastructure.django.repositories import DjangoProjectRepository
from apps.projects.tasks import process_uploaded_project_task

_repository = DjangoProjectRepository()


class ProjectUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = ProjectUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        uploaded_file = serializer.validated_data["file"]

        service = UploadProjectService(
            repository=_repository,
            max_file_size_bytes=settings.PROJECT_UPLOAD_MAX_SIZE_BYTES,
            allowed_content_types=settings.PROJECT_UPLOAD_ALLOWED_CONTENT_TYPES,
        )
        entity = service.upload(
            owner_id=request.user.id,
            title=serializer.validated_data["title"],
            description=serializer.validated_data.get("description", ""),
            file=uploaded_file,
            file_name=uploaded_file.name,
            file_size=uploaded_file.size,
            content_type=uploaded_file.content_type,
        )

        # Background: checksum/validate the stored file, then flip status
        # and notify. Kept out of the request/response cycle entirely.
        process_uploaded_project_task.delay(str(entity.id))
        create_notification_task.delay(
            user_id=str(entity.owner_id),
            verb="project_uploaded",
            message=f"'{entity.title}' was uploaded and is now processing.",
            level="info",
        )

        return Response(ProjectSerializer(entity.__dict__).data, status=201)


class MyProjectsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        service = ListMyProjectsService(repository=_repository)
        entities = service.list_for_owner(request.user.id)
        data = ProjectSerializer([e.__dict__ for e in entities], many=True).data
        return Response(data)


class ProjectDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        service = GetProjectForDownloadService(repository=_repository)
        file_path = service.get_file_path(project_id=project_id, owner_id=request.user.id)
        return FileResponse(open(file_path, "rb"), as_attachment=True)
