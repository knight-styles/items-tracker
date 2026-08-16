import calendar
from datetime import timedelta

from django.db.models import Count, Sum
from django.shortcuts import render
from django.utils import timezone

from ..models import AppSettings, Employee, Item, UsageLog, User
from ..permissions import admin_required


@admin_required
def admin_dashboard(request):
    app_settings = AppSettings.load()
    now = timezone.now()
    today = timezone.localtime(now).date()

    # 1. Base KPIs
    total_employees = Employee.objects.filter(is_active=True).count()
    total_items = Item.objects.filter(is_active=True).count()
    total_supervisors = User.objects.filter(role=User.Role.SUPERVISOR, is_superuser=False, is_active=True).count()

    # 2. Stock Health Metrics
    all_active_items = Item.objects.filter(is_active=True)
    total_stock_qty = all_active_items.aggregate(total=Sum("current_stock"))["total"] or 0

    healthy_stock_count = all_active_items.filter(current_stock__gt=app_settings.low_stock_threshold).count()
    low_stock_count = all_active_items.filter(current_stock__gt=0, current_stock__lte=app_settings.low_stock_threshold).count()
    out_of_stock_count = all_active_items.filter(current_stock__lte=0).count()

    healthy_pct = int((healthy_stock_count / total_items) * 100) if total_items > 0 else 0
    low_stock_pct = int((low_stock_count / total_items) * 100) if total_items > 0 else 0
    out_of_stock_pct = int((out_of_stock_count / total_items) * 100) if total_items > 0 else 0

    low_stock_list = list(all_active_items.filter(current_stock__lte=app_settings.low_stock_threshold).order_by("current_stock")[:5])

    # Stock Distribution per Item Type
    stock_distribution = []
    for item in all_active_items.order_by("-current_stock")[:6]:
        item_pct = int((max(0, item.current_stock) / max(1, total_stock_qty)) * 100) if total_stock_qty > 0 else 0
        stock_distribution.append({
            "name": item.name,
            "stock": item.current_stock,
            "pct": item_pct,
            "is_low": item.current_stock <= app_settings.low_stock_threshold
        })

    # 3. Monthly Comparison Analytics (Past 4 Months - Range-Indexed Lookup)
    monthly_trend = []
    max_month_count = 0
    current_year = today.year
    current_month = today.month

    for i in range(3, -1, -1):
        target_month = current_month - i
        target_year = current_year
        while target_month <= 0:
            target_month += 12
            target_year -= 1

        first_day_dt = timezone.make_aware(timezone.datetime(target_year, target_month, 1, 0, 0, 0))
        last_day_num = calendar.monthrange(target_year, target_month)[1]
        next_month_dt = first_day_dt + timedelta(days=last_day_num)

        m_count = UsageLog.objects.filter(logged_at__gte=first_day_dt, logged_at__lt=next_month_dt).aggregate(total=Sum("quantity"))["total"] or 0

        if m_count > max_month_count:
            max_month_count = m_count

        month_label = first_day_dt.strftime("%b %Y")
        monthly_trend.append({
            "month_name": first_day_dt.strftime("%b"),
            "full_label": month_label,
            "count": m_count,
            "is_current": (i == 0)
        })

    # Compute percentage growth & bar heights for monthly graph
    prev_m_count = None
    for m in monthly_trend:
        m["pct"] = int((m["count"] / max_month_count) * 100) if max_month_count > 0 else 0
        if prev_m_count is not None and prev_m_count > 0:
            m["change_pct"] = round(((m["count"] - prev_m_count) / prev_m_count) * 100, 1)
        else:
            m["change_pct"] = 0.0
        prev_m_count = m["count"]

    # 4. Financial & Cost Savings Analytics
    total_issued_30d = UsageLog.objects.filter(logged_at__gte=now - timedelta(days=30)).aggregate(total=Sum("quantity"))["total"] or 0
    est_units_saved = round(total_issued_30d * 0.25)
    est_unit_cost = 25  # Avg unit cost in $ / ₹ equivalent
    est_financial_savings = est_units_saved * est_unit_cost

    active_emp_logging = UsageLog.objects.filter(logged_at__gte=now - timedelta(days=30)).values("employee").distinct().count()
    compliance_rate = int((active_emp_logging / total_employees) * 100) if total_employees > 0 else 0

    # 5. 7-Day Daily Trend Chart Data (Range-Indexed Lookup)
    trend = []
    max_day_count = 0
    peak_day = None
    peak_count = -1

    for i in range(6, -1, -1):
        day_date = today - timedelta(days=i)
        day_start = timezone.make_aware(timezone.datetime(day_date.year, day_date.month, day_date.day, 0, 0, 0))
        day_end = day_start + timedelta(days=1)

        count = UsageLog.objects.filter(logged_at__gte=day_start, logged_at__lt=day_end).aggregate(total=Sum("quantity"))["total"] or 0
        if count > max_day_count:
            max_day_count = count
        if count > peak_count:
            peak_count = count
            peak_day = day_date.strftime("%A")
        trend.append({
            "date": day_date,
            "label": day_date.strftime("%a"),
            "full_date": day_date.strftime("%b %d"),
            "count": count
        })

    for t in trend:
        t["pct"] = int((t["count"] / max_day_count) * 100) if max_day_count > 0 else 0
        t["is_peak"] = (t["count"] == peak_count and peak_count > 0)

    # 6. Top 5 Most Issued Safety Items (Past 30 Days)
    thirty_days_ago = now - timedelta(days=30)
    top_items_qs = UsageLog.objects.filter(logged_at__gte=thirty_days_ago)\
        .values("item__name", "item__current_stock")\
        .annotate(total_issued=Sum("quantity"))\
        .order_by("-total_issued")[:5]

    total_issued_top = sum(item["total_issued"] for item in top_items_qs) or 1
    top_items = []
    for item in top_items_qs:
        item["pct"] = int((item["total_issued"] / total_issued_top) * 100)
        top_items.append(item)

    # 7. High-Frequency Replacement Anomaly Monitor (OPTIMIZED DB AGGREGATION - 1 ROW PER EMP)
    fourteen_days_ago = now - timedelta(days=14)
    anomalies_qs = (
        UsageLog.objects.filter(logged_at__gte=fourteen_days_ago)
        .values("employee__id", "employee__name", "employee__code")
        .annotate(total_reallocations=Count("id"), total_qty=Sum("quantity"))
        .filter(total_reallocations__gte=2)
        .order_by("-total_reallocations")[:5]
    )

    anomalies_list = []
    for a in anomalies_qs:
        emp_id = a["employee__id"]
        item_counts = (
            UsageLog.objects.filter(logged_at__gte=fourteen_days_ago, employee_id=emp_id)
            .values("item__name")
            .annotate(qty=Sum("quantity"))
        )
        item_summaries = [f"{i['item__name']} ({i['qty']}x)" for i in item_counts]
        anomalies_list.append({
            "employee_name": a["employee__name"],
            "employee_code": a["employee__code"],
            "items_summary": ", ".join(item_summaries),
            "total_reallocations": a["total_reallocations"],
            "total_qty": a["total_qty"]
        })

    total_allocations_14d = UsageLog.objects.filter(logged_at__gte=fourteen_days_ago).count()

    if total_allocations_14d > 0:
        variance_rate = round((sum(a["total_reallocations"] for a in anomalies_list) / total_allocations_14d) * 100, 1)
        integrity_score = max(0.0, round(100.0 - variance_rate, 1))
    else:
        variance_rate = 0.0
        integrity_score = 100.0

    context = {
        "active_nav": "dashboard",
        "total_employees": total_employees,
        "total_items": total_items,
        "total_supervisors": total_supervisors,
        "total_stock_qty": total_stock_qty,
        "healthy_stock_count": healthy_stock_count,
        "healthy_pct": healthy_pct,
        "low_stock_items": low_stock_count,
        "low_stock_pct": low_stock_pct,
        "out_of_stock_count": out_of_stock_count,
        "out_of_stock_pct": out_of_stock_pct,
        "low_stock_list": low_stock_list,
        "stock_distribution": stock_distribution,
        "monthly_trend": monthly_trend,
        "total_issued_30d": total_issued_30d,
        "est_units_saved": est_units_saved,
        "est_financial_savings": est_financial_savings,
        "compliance_rate": compliance_rate,
        "trend": trend,
        "peak_day": peak_day if peak_count > 0 else None,
        "peak_count": peak_count if peak_count > 0 else 0,
        "top_items": top_items,
        "anomalies_list": anomalies_list,
        "variance_rate": variance_rate,
        "integrity_score": integrity_score,
    }
    return render(request, "tracker/admin/dashboard.html", context)
