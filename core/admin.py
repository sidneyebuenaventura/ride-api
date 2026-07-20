from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from core.models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Ride role", {"fields": ("role", "phone_number")}),
    )
    list_display = ("username", "email", "role", "is_staff")
    list_filter = UserAdmin.list_filter + ("role",)
