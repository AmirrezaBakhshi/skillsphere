from django.conf import settings
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.api.serializers import (
    GoogleLoginSerializer,
    LoginSerializer,
    RegisterSerializer,
    UserSerializer,
)
from apps.users.application.services import (
    AuthenticationService,
    GoogleAuthenticationService,
    RegistrationService,
)
from apps.users.infrastructure.django.google_oauth import verify_google_id_token
from apps.users.infrastructure.django.models import User
from apps.users.infrastructure.django.repositories import DjangoUserRepository

_repository = DjangoUserRepository()


def _issue_tokens_for(entity_id) -> RefreshToken:
    # Token generation needs the concrete Django model instance; this is
    # the one place infrastructure reaches back into the ORM directly,
    # which is fine since issuing a JWT is itself an infrastructure concern.
    orm_user = User.objects.get(id=entity_id)
    return RefreshToken.for_user(orm_user)


def _auth_response(entity) -> Response:
    refresh = _issue_tokens_for(entity.id)
    response = Response(
        {
            "user": UserSerializer.from_entity(entity).data,
            "access": str(refresh.access_token),
        }
    )
    response.set_cookie(
        key=settings.JWT_REFRESH_COOKIE_NAME,
        value=str(refresh),
        httponly=True,
        secure=not settings.DEBUG,
        samesite="Lax",
        path=settings.JWT_REFRESH_COOKIE_PATH,
        max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
    )
    return response


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = RegistrationService(repository=_repository)
        entity = service.register(**serializer.validated_data)
        return _auth_response(entity)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = AuthenticationService(repository=_repository)
        entity = service.authenticate(**serializer.validated_data)
        return _auth_response(entity)


class GoogleLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = GoogleLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        google_profile = verify_google_id_token(serializer.validated_data["id_token"])

        service = GoogleAuthenticationService(repository=_repository)
        entity = service.authenticate_or_register(
            email=google_profile.email,
            google_sub=google_profile.sub,
            username_hint=google_profile.email.split("@")[0],
        )
        return _auth_response(entity)


class RefreshView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        raw_refresh = request.COOKIES.get(settings.JWT_REFRESH_COOKIE_NAME)
        if not raw_refresh:
            return Response({"detail": "Refresh cookie missing"}, status=401)

        try:
            refresh = RefreshToken(raw_refresh)
            new_access = str(refresh.access_token)
        except TokenError:
            return Response({"detail": "Refresh token invalid or expired"}, status=401)

        response = Response({"access": new_access})

        if settings.SIMPLE_JWT["ROTATE_REFRESH_TOKENS"]:
            refresh.set_jti()
            refresh.set_exp()
            response.set_cookie(
                key=settings.JWT_REFRESH_COOKIE_NAME,
                value=str(refresh),
                httponly=True,
                secure=not settings.DEBUG,
                samesite="Lax",
                path=settings.JWT_REFRESH_COOKIE_PATH,
                max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
            )
        return response


class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        raw_refresh = request.COOKIES.get(settings.JWT_REFRESH_COOKIE_NAME)
        if raw_refresh:
            try:
                RefreshToken(raw_refresh).blacklist()
            except TokenError:
                pass
        response = Response(status=204)
        response.delete_cookie(settings.JWT_REFRESH_COOKIE_NAME, path=settings.JWT_REFRESH_COOKIE_PATH)
        return response


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        entity = _repository.get_by_id(request.user.id)
        return Response(UserSerializer.from_entity(entity).data)
