from urllib.parse import urlencode

from django.contrib import messages
from django.db import transaction
from django.db.models import F
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from ..models import AppSettings, Employee, Item, UsageLog
from ..permissions import supervisor_required
from ..search_utils import fuzzy_filter_and_rank
from ..usage_status import compute_item_status

MAX_ITEM_ROWS = 5


@supervisor_required
def supervisor_log(request):
    app_settings = AppSettings.load()
    is_bulk_disabled, cooldown_end, remaining_days = app_settings.is_bulk_issue_disabled()
    return render(
        request,
        "tracker/supervisor/log.html",
        {
            "active_nav": "log",
            "app_settings": app_settings,
            "max_item_rows": MAX_ITEM_ROWS,
            "is_bulk_disabled": is_bulk_disabled,
            "cooldown_end": cooldown_end,
            "remaining_days": remaining_days,
        },
    )


@supervisor_required
def supervisor_log_employee_search(request):
    q = request.GET.get("q", "").strip()
    employees_qs = Employee.objects.filter(is_active=True)
    if q:
        ranked_employees, _ = fuzzy_filter_and_rank(employees_qs, q, ["name", "code"])
        employees = ranked_employees[:10]
    else:
        employees = list(employees_qs.order_by("name")[:10])
    return JsonResponse({
        "results": [{"id": e.pk, "name": e.name, "code": e.code} for e in employees]
    })


@supervisor_required
def supervisor_log_item_options(request):
    employee_id = request.GET.get("employee_id", "")
    if not employee_id.isdigit():
        return JsonResponse({"error": "Invalid employee."}, status=400)

    employee = get_object_or_404(Employee, pk=employee_id, is_active=True)
    app_settings = AppSettings.load()
    now = timezone.now()

    active_items = list(Item.objects.filter(is_active=True).order_by("name"))
    active_item_ids = [item.pk for item in active_items]

    # Single query for all relevant logs (BUG-3 fix: was N+1, now 1 query)
    recent_logs = (
        UsageLog.objects
        .filter(employee=employee, item_id__in=active_item_ids)
        .order_by("item_id", "-logged_at")
        .values("item_id", "logged_at")
    )
    # Build item_id -> most-recent logged_at (first entry per item due to ordering)
    last_log_map = {}
    for log in recent_logs:
        if log["item_id"] not in last_log_map:
            last_log_map[log["item_id"]] = log["logged_at"]

    results = []
    for item in active_items:
        last_log_at = last_log_map.get(item.pk)
        status = compute_item_status(last_log_at, app_settings, now=now)
        results.append({
            "id": item.pk,
            "name": item.name,
            "status": status,
            "stock": item.current_stock,
            "image_url": item.get_image_url(),
        })

    return JsonResponse({
        "results": results,
        "colors": {"today": app_settings.color_today, "period": app_settings.color_period},
    })


@supervisor_required
@require_POST
def supervisor_log_submit(request):
    employee_id = request.POST.get("employee_id")
    item_ids = [v for v in request.POST.getlist("item") if v]

    employee = None
    if employee_id and employee_id.isdigit():
        employee = Employee.objects.filter(pk=employee_id, is_active=True).first()

    if not employee:
        messages.error(request, "Please select a valid employee before logging.")
        return redirect("supervisor_log")

    if not item_ids:
        messages.error(request, "Select at least one item to log.")
        return redirect("supervisor_log")

    if not all(v.isdigit() for v in item_ids):
        messages.error(request, "One or more selected items are invalid.")
        return redirect("supervisor_log")

    if len(item_ids) != len(set(item_ids)):
        messages.error(request, "The same item was selected more than once. Each item can only be logged once per submission.")
        return redirect("supervisor_log")

    items = list(Item.objects.filter(pk__in=item_ids, is_active=True))
    if len(items) != len(item_ids):
        messages.error(request, "One or more selected items are no longer available.")
        return redirect("supervisor_log")

    logs = []
    with transaction.atomic():
        for item in items:
            logs.append(
                UsageLog(
                    employee=employee,
                    item=item,
                    quantity=1,
                    logged_by=request.user,
                )
            )

        UsageLog.objects.bulk_create(logs)
        for item in items:
            Item.objects.filter(pk=item.pk).update(current_stock=F("current_stock") - 1)

    logged_names = ", ".join(i.name for i in items)
    query_param = urlencode({"logged": "1", "prefill_employee_id": str(employee.pk), "emp": employee.name, "items": logged_names})
    return redirect(f"{reverse('supervisor_log')}?{query_param}")


@supervisor_required
@require_POST
def supervisor_bulk_periodic_allocate(request):
    app_settings = AppSettings.load()
    is_disabled, cooldown_end, remaining_days = app_settings.is_bulk_issue_disabled()

    if is_disabled:
        last_date_str = app_settings.last_bulk_issue_at.strftime('%d %b %Y') if app_settings.last_bulk_issue_at else ""
        messages.error(
            request,
            f"Bulk periodic allocation was already completed on {last_date_str}. Next allotment available in {remaining_days} days."
        )
        return redirect("supervisor_log")

    active_employees = list(Employee.objects.filter(is_active=True))
    active_items = list(Item.objects.filter(is_active=True))

    if not active_employees:
        messages.error(request, "No active employees found for bulk periodic kit allocation.")
        return redirect("supervisor_log")

    if not active_items:
        messages.error(request, "No active items found for bulk periodic kit allocation.")
        return redirect("supervisor_log")

    created_logs_count = 0
    employees_allocated_count = 0

    with transaction.atomic():
        all_logs = []
        for employee in active_employees:
            for item in active_items:
                all_logs.append(
                    UsageLog(
                        employee=employee,
                        item=item,
                        quantity=1,
                        logged_by=request.user,
                    )
                )
                created_logs_count += 1
            employees_allocated_count += 1

        # 1. Bulk insert all UsageLog records in 1,000-row batch queries
        UsageLog.objects.bulk_create(all_logs, batch_size=1000)

        # 2. Bulk update item stock level ONCE per item category
        num_employees = len(active_employees)
        for item in active_items:
            Item.objects.filter(pk=item.pk).update(current_stock=F("current_stock") - num_employees)

        app_settings.last_bulk_issue_at = timezone.now()
        app_settings.save()

    messages.success(
        request,
        f"Bulk Periodic Kit Allocation Complete! Issued 1 piece of all {len(active_items)} active safety items to {employees_allocated_count} active employees ({created_logs_count} total logs recorded)."
    )
    return redirect("supervisor_log")
