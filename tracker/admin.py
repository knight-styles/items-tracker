from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import AppSettings, AuditLog, Employee, Item, StockUpdate, User, UsageLog


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Role", {"fields": ("role", "created_by")}),
    )
    list_display = ("username", "first_name", "last_name", "role", "is_active", "is_superuser")
    list_filter = ("role", "is_active", "is_superuser")


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active", "created_by", "created_at", "updated_by", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "code")


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("name", "current_stock", "is_active", "created_by", "created_at", "updated_by", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(AppSettings)
class AppSettingsAdmin(admin.ModelAdmin):
    list_display = ("period_days", "reset_mode", "reset_time", "reset_hours", "low_stock_threshold")

    def has_add_permission(self, request):
        return not AppSettings.objects.exists()


@admin.register(UsageLog)
class UsageLogAdmin(admin.ModelAdmin):
    list_display = ("employee", "item", "quantity", "logged_by", "logged_at")
    list_filter = ("item", "logged_at")
    search_fields = ("employee__name", "employee__code", "item__name")
    date_hierarchy = "logged_at"


@admin.register(StockUpdate)
class StockUpdateAdmin(admin.ModelAdmin):
    list_display = ("item", "quantity_added", "updated_by", "updated_at")
    list_filter = ("item", "updated_at")
    date_hierarchy = "updated_at"


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("actor", "action", "target_type", "target_repr", "created_at")
    list_filter = ("action", "target_type")
    search_fields = ("target_repr", "details")
    date_hierarchy = "created_at"
