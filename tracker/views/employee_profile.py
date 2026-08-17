"""
Employee Equipment History Card — dedicated profile page showing currently-held
equipment, KPI statistics, and full usage history for a single employee.
"""
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Max, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from ..models import AppSettings, Employee, Item, UsageLog
from ..usage_status import compute_item_status

HISTORY_PAGE_SIZE = 20


def _parse_date(s):
    if not s:
        return None
    from datetime import datetime
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


@login_required
def employee_profile(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    app_settings = AppSettings.load()
    now = timezone.now()
    today = timezone.localtime(now).date()
    start_of_week = today - timedelta(days=today.weekday())
    start_of_month = today.replace(day=1)

    # ── KPI Aggregation (single query) ──────────────────────────────────
    kpis = UsageLog.objects.filter(employee=employee).aggregate(
        total_all_time=Coalesce(Sum("quantity"), Value(0)),
        total_today=Coalesce(
            Sum("quantity", filter=Q(logged_at__date=today)), Value(0)
        ),
        total_week=Coalesce(
            Sum("quantity", filter=Q(logged_at__date__gte=start_of_week)), Value(0)
        ),
        total_month=Coalesce(
            Sum("quantity", filter=Q(logged_at__date__gte=start_of_month)), Value(0)
        ),
    )

    # ── Equipment Cards ─────────────────────────────────────────────────
    # For each active item, get the employee's most recent log + total count
    equipment_cards = []
    items_with_stats = (
        Item.objects.filter(is_active=True, usage_logs__employee=employee)
        .annotate(
            last_issued_at=Max("usage_logs__logged_at", filter=Q(usage_logs__employee=employee)),
            times_issued=Count("usage_logs", filter=Q(usage_logs__employee=employee)),
            qty_issued=Coalesce(
                Sum("usage_logs__quantity", filter=Q(usage_logs__employee=employee)),
                Value(0),
            ),
        )
        .distinct()
        .order_by("-last_issued_at")
    )

    for item in items_with_stats:
        status = compute_item_status(item.last_issued_at, app_settings, now=now)
        equipment_cards.append({
            "item": item,
            "image_url": item.get_image_url(),
            "last_issued_at": item.last_issued_at,
            "times_issued": item.times_issued,
            "qty_issued": item.qty_issued,
            "status": status,
            "status_color": (
                app_settings.color_today if status == "today"
                else app_settings.color_period if status == "period"
                else ""
            ),
        })

    # ── History Table (paginated, with date filter) ─────────────────────
    date_from_str = request.GET.get("date_from", "")
    date_to_str = request.GET.get("date_to", "")
    d_from = _parse_date(date_from_str)
    d_to = _parse_date(date_to_str)

    history_qs = (
        UsageLog.objects.filter(employee=employee)
        .select_related("item", "logged_by")
    )
    if d_from:
        history_qs = history_qs.filter(logged_at__date__gte=d_from)
    if d_to:
        history_qs = history_qs.filter(logged_at__date__lte=d_to)

    paginator = Paginator(history_qs, HISTORY_PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    # Build base query string for pagination links (preserve filters)
    qs_params = request.GET.copy()
    qs_params.pop("page", None)
    base_qs = qs_params.urlencode()

    context = {
        "active_nav": "reports",
        "employee": employee,
        "kpis": kpis,
        "equipment_cards": equipment_cards,
        "equipment_count": len(equipment_cards),
        "page_obj": page_obj,
        "result_count": history_qs.count(),
        "date_from": date_from_str,
        "date_to": date_to_str,
        "base_qs": base_qs,
        "app_settings": app_settings,
    }
    return render(request, "tracker/employee_profile.html", context)
