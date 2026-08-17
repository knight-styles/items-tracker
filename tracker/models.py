from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
import math


class User(AbstractUser):
    """
    Custom user model with a role field.
    - 'admin' role: full access (Employees, Items, Users, Reports, Settings, Dashboard)
    - 'supervisor' role: operational access (Log, Add Employee, Reports, Stock)

    Note: Django superusers (created via createsuperuser) are treated as Admins
    regardless of the role field, so the very first account always has full
    access even before any role-based Admin exists.
    """

    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        SUPERVISOR = "supervisor", "Supervisor"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.SUPERVISOR,
    )

    # Track who created a supervisor account, for auditing on the Users tab
    created_by = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_users",
    )

    def is_admin(self):
        return self.is_superuser or self.role == self.Role.ADMIN

    def is_supervisor(self):
        return self.role == self.Role.SUPERVISOR and not self.is_superuser

    def __str__(self):
        return self.username


class Employee(models.Model):
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=50, unique=True, help_text="Employee ID / code used for search")
    is_active = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.code})"


class Item(models.Model):
    name = models.CharField(max_length=150, unique=True)
    current_stock = models.IntegerField(default=0, help_text="Can go negative if usage exceeds recorded stock")
    image = models.ImageField(
        upload_to="item_images/",
        null=True,
        blank=True,
        help_text="Upload unique image for this equipment item",
    )
    is_active = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def get_image_url(self):
        if self.image:
            try:
                return self.image.url
            except ValueError:
                pass
        name_lower = self.name.lower()
        if "helmet" in name_lower or "hard hat" in name_lower:
            return "/static/images/items/helmet.jpg"
        elif "goggle" in name_lower or "glass" in name_lower:
            return "/static/images/items/goggles.jpg"
        elif "glove" in name_lower:
            return "/static/images/items/gloves.jpg"
        elif "vest" in name_lower or "jacket" in name_lower:
            return "/static/images/items/vest.jpg"
        elif "boot" in name_lower or "shoe" in name_lower:
            return "/static/images/items/boots.jpg"
        return ""

    def __str__(self):
        return self.name


class AppSettings(models.Model):
    """
    Singleton settings row (always pk=1). Use AppSettings.load() to fetch it
    -- creates the row with defaults on first access so the app works even
    before Admin has visited the Settings tab.
    """

    class ResetMode(models.TextChoices):
        FIXED_TIME = "fixed_time", "Reset at a fixed time each day"
        HOURS_AFTER = "hours_after", "Reset N hours after each assignment"

    period_days = models.PositiveIntegerField(
        default=7, help_text="How many days an item stays highlighted after an employee takes it"
    )
    reset_mode = models.CharField(max_length=20, choices=ResetMode.choices, default=ResetMode.FIXED_TIME)
    reset_time = models.TimeField(
        default="00:00", help_text="Used when reset mode is 'fixed time'. The 'today' highlight clears at this time."
    )
    reset_hours = models.PositiveIntegerField(
        default=20, help_text="Used when reset mode is 'hours after'. Hours after taking an item before it stops counting as 'today'."
    )
    color_today = models.CharField(max_length=7, default="#dc2626", help_text="Color for items taken today (or within the reset window)")
    color_period = models.CharField(max_length=7, default="#2563eb", help_text="Color for items taken within the period window")
    low_stock_threshold = models.PositiveIntegerField(default=5, help_text="Items at or below this stock level are flagged low on the Items/Stock tabs")
    bulk_issue_cooldown_days = models.PositiveIntegerField(
        default=30, help_text="Number of days Bulk Issue button remains disabled after execution to prevent duplicate periodic allotment"
    )
    last_bulk_issue_at = models.DateTimeField(
        null=True, blank=True, help_text="Timestamp of the last bulk periodic allotment execution"
    )

    def is_bulk_issue_disabled(self):
        if not self.last_bulk_issue_at:
            return False, None, 0
        from datetime import timedelta
        from django.utils import timezone
        now = timezone.now()
        cooldown_end = self.last_bulk_issue_at + timedelta(days=self.bulk_issue_cooldown_days)
        if now < cooldown_end:
            remaining_seconds = (cooldown_end - now).total_seconds()
            remaining_days = math.ceil(remaining_seconds / 86400)
            return True, cooldown_end, remaining_days
        return False, None, 0

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass  # singleton row is never deleted

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        if created:
            # get_or_create's newly-created instance carries raw Python field
            # defaults (e.g. reset_time as the string "00:00") rather than
            # properly-typed values (a real datetime.time). Refreshing from
            # the DB forces Django to re-parse them correctly, so callers
            # always get a consistently-typed object.
            obj.refresh_from_db()
        return obj

    def __str__(self):
        return "App Settings"


class UsageLog(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="usage_logs")
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="usage_logs")
    quantity = models.PositiveIntegerField(default=1)
    logged_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    logged_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-logged_at"]

    def __str__(self):
        return f"{self.employee} took {self.quantity}x {self.item} at {self.logged_at:%Y-%m-%d %H:%M}"


class StockUpdate(models.Model):
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="stock_updates")
    quantity_added = models.PositiveIntegerField()
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"+{self.quantity_added} to {self.item} at {self.updated_at:%Y-%m-%d %H:%M}"


class AuditLog(models.Model):
    """
    Tracks sensitive actions across the app (deletes, deactivations, settings
    changes, password resets) independent of the per-record created_by/
    updated_by fields already on Employee/Item. This gives a single
    chronological trail Admin can review.
    """

    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=50)
    target_type = models.CharField(max_length=50)
    target_repr = models.CharField(max_length=255)
    details = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.actor}: {self.action} {self.target_type} '{self.target_repr}'"
