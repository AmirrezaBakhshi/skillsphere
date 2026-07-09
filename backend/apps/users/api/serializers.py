from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.users.domain.entities import UserEntity


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True)

    def validate_password(self, value: str) -> str:
        validate_password(value)
        return value


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class GoogleLoginSerializer(serializers.Serializer):
    id_token = serializers.CharField(write_only=True)


class UserSerializer(serializers.Serializer):
    """Read-only representation of a UserEntity for API responses."""

    id = serializers.UUIDField()
    email = serializers.EmailField()
    username = serializers.CharField()
    is_staff = serializers.BooleanField()
    date_joined = serializers.DateTimeField()

    @classmethod
    def from_entity(cls, entity: UserEntity) -> "UserSerializer":
        return cls(instance=entity.__dict__)
