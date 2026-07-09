from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.users.infrastructure.django.models import User


@admin.register(User)
class SkillSphereUserAdmin(UserAdmin):
    list_display = ("email", "username", "is_staff", "is_active", "date_joined")
    ordering = ("-date_joined",)
    search_fields = ("email", "username")
    fieldsets = UserAdmin.fieldsets + (("Profile", {"fields": ("bio", "avatar", "google_sub")}),)
