from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import redirect, render

from ..audit import log_audit
from ..forms import SettingsForm
from ..models import AppSettings, AuditLog
from ..permissions import admin_required

AUDIT_PAGE_SIZE = 30


@admin_required
def admin_settings(request):
    app_settings = AppSettings.load()
    if request.method == "POST":
        form = SettingsForm(request.POST, instance=app_settings)
        if form.is_valid():
            changed_fields = form.changed_data
            form.save()
            if changed_fields:
                log_audit(
                    request.user, "settings_update", "AppSettings", "App Settings",
                    details=f"changed: {', '.join(changed_fields)}",
                )
            messages.success(request, "Settings updated.")
            return redirect("admin_settings")
    else:
        form = SettingsForm(instance=app_settings)
    return render(request, "tracker/admin/settings_form.html", {"form": form, "active_nav": "settings"})


@admin_required
def admin_audit_log(request):
    entries = AuditLog.objects.select_related("actor").all()
    action = request.GET.get("action", "").strip()
    if action:
        entries = entries.filter(action=action)

    paginator = Paginator(entries, AUDIT_PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    action_choices = (
        AuditLog.objects.order_by().values_list("action", flat=True).distinct()
    )

    return render(
        request,
        "tracker/admin/audit_log.html",
        {
            "active_nav": "settings",
            "page_obj": page_obj,
            "results": page_obj.object_list,
            "action_filter": action,
            "action_choices": sorted(action_choices),
        },
    )
