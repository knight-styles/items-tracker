import csv

import calendar
from datetime import date, datetime as dt, timedelta
import io

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import IntegerField, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Font

from ..forms import EmployeeSearchForm, StockReportFilterForm, UsageReportFilterForm
from ..models import Employee, Item, StockUpdate, UsageLog
from ..search_utils import fuzzy_filter_and_rank

REPORT_PAGE_SIZE = 25


def _generate_month_choices():
    today = timezone.localtime(timezone.now()).date()
    start_of_month = today.replace(day=1)
    choices = [
        ("", "Select Month"),
        ("this_month", f"Current Month ({start_of_month.strftime('%B %Y')})"),
        ("last_month", "Last Month"),
    ]
    curr_year, curr_month = today.year, today.month
    for i in range(1, 12):
        m = curr_month - i
        y = curr_year
        while m <= 0:
            m += 12
            y -= 1
        d_obj = date(y, m, 1)
        val = f"{y:04d}-{m:02d}"
        choices.append((val, d_obj.strftime("%B %Y")))
    return choices


def _filtered_usage_queryset(get_params):
    form = UsageReportFilterForm(get_params or None)
    qs = UsageLog.objects.select_related("employee", "item", "logged_by").all()
    sort = "-logged_at"
    if form.is_valid():
        date_from = form.cleaned_data.get("date_from")
        date_to = form.cleaned_data.get("date_to")
        employee = form.cleaned_data.get("employee")
        item = form.cleaned_data.get("item")
        sort = form.cleaned_data.get("sort") or sort
        if date_from:
            qs = qs.filter(logged_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(logged_at__date__lte=date_to)
        if employee:
            qs = qs.filter(employee=employee)
        if item:
            qs = qs.filter(item=item)
    return form, qs.order_by(sort)


def _filtered_stock_queryset(get_params):
    form = StockReportFilterForm(get_params or None)
    qs = StockUpdate.objects.select_related("item", "updated_by").all()
    today = timezone.localtime(timezone.now()).date()
    start_of_week = today - timedelta(days=today.weekday())
    start_of_month = today.replace(day=1)

    period = get_params.get("period", "") if get_params else ""
    date_from_str = get_params.get("date_from", "") if get_params else ""
    date_to_str = get_params.get("date_to", "") if get_params else ""

    if period == "this_week":
        end_of_week = start_of_week + timedelta(days=6)
        date_from_str = start_of_week.strftime("%Y-%m-%d")
        date_to_str = end_of_week.strftime("%Y-%m-%d")
    elif period in ("this_month", "current_month"):
        _, last_day = calendar.monthrange(today.year, today.month)
        end_of_month = today.replace(day=last_day)
        date_from_str = start_of_month.strftime("%Y-%m-%d")
        date_to_str = end_of_month.strftime("%Y-%m-%d")
        period = "this_month"
    elif period == "last_month":
        if today.month == 1:
            lm_year, lm_month = today.year - 1, 12
        else:
            lm_year, lm_month = today.year, today.month - 1
        _, lm_last_day = calendar.monthrange(lm_year, lm_month)
        date_from_str = date(lm_year, lm_month, 1).strftime("%Y-%m-%d")
        date_to_str = date(lm_year, lm_month, lm_last_day).strftime("%Y-%m-%d")
    elif period and len(period) == 7 and "-" in period:
        try:
            y, m = map(int, period.split("-"))
            _, lm_last_day = calendar.monthrange(y, m)
            date_from_str = date(y, m, 1).strftime("%Y-%m-%d")
            date_to_str = date(y, m, lm_last_day).strftime("%Y-%m-%d")
        except ValueError:
            pass

    d_from = _parse_date(date_from_str)
    d_to = _parse_date(date_to_str)

    if d_from:
        qs = qs.filter(updated_at__date__gte=d_from)
    if d_to:
        qs = qs.filter(updated_at__date__lte=d_to)

    sort = "-updated_at"
    if form.is_valid():
        date_from = form.cleaned_data.get("date_from")
        date_to = form.cleaned_data.get("date_to")
        item = form.cleaned_data.get("item")
        sort = form.cleaned_data.get("sort") or sort
        if date_from and not d_from:
            qs = qs.filter(updated_at__date__gte=date_from)
        if date_to and not d_to:
            qs = qs.filter(updated_at__date__lte=date_to)
        if item:
            qs = qs.filter(item=item)
    return form, qs.order_by(sort), date_from_str, date_to_str, period


def _employee_summary_queryset(get_params):
    """
    One row per employee with item counts for today / this week / this month,
    plus support for quick period filters (this_week, this_month, last_month, YYYY-MM)
    and typo-tolerant fuzzy search.
    """
    form = EmployeeSearchForm(get_params or None)
    today = timezone.localtime(timezone.now()).date()
    start_of_week = today - timedelta(days=today.weekday())
    start_of_month = today.replace(day=1)

    period = get_params.get("period", "") if get_params else ""
    date_from_str = get_params.get("date_from", "") if get_params else ""
    date_to_str = get_params.get("date_to", "") if get_params else ""

    if period == "this_week":
        end_of_week = start_of_week + timedelta(days=6)
        date_from_str = start_of_week.strftime("%Y-%m-%d")
        date_to_str = end_of_week.strftime("%Y-%m-%d")
    elif period in ("this_month", "current_month"):
        _, last_day = calendar.monthrange(today.year, today.month)
        end_of_month = today.replace(day=last_day)
        date_from_str = start_of_month.strftime("%Y-%m-%d")
        date_to_str = end_of_month.strftime("%Y-%m-%d")
        period = "this_month"
    elif period == "last_month":
        if today.month == 1:
            lm_year, lm_month = today.year - 1, 12
        else:
            lm_year, lm_month = today.year, today.month - 1
        _, lm_last_day = calendar.monthrange(lm_year, lm_month)
        date_from_str = date(lm_year, lm_month, 1).strftime("%Y-%m-%d")
        date_to_str = date(lm_year, lm_month, lm_last_day).strftime("%Y-%m-%d")
    elif period and len(period) == 7 and "-" in period:
        try:
            y, m = map(int, period.split("-"))
            _, lm_last_day = calendar.monthrange(y, m)
            date_from_str = date(y, m, 1).strftime("%Y-%m-%d")
            date_to_str = date(y, m, lm_last_day).strftime("%Y-%m-%d")
        except ValueError:
            pass

    d_from = _parse_date(date_from_str)
    d_to = _parse_date(date_to_str)

    period_filter = Q()
    if d_from:
        period_filter &= Q(usage_logs__logged_at__date__gte=d_from)
    if d_to:
        period_filter &= Q(usage_logs__logged_at__date__lte=d_to)

    qs = Employee.objects.annotate(
        count_today=Coalesce(
            Sum("usage_logs__quantity", filter=Q(usage_logs__logged_at__date=today)),
            Value(0), output_field=IntegerField(),
        ),
        count_week=Coalesce(
            Sum("usage_logs__quantity", filter=Q(usage_logs__logged_at__date__gte=start_of_week)),
            Value(0), output_field=IntegerField(),
        ),
        count_month=Coalesce(
            Sum("usage_logs__quantity", filter=Q(usage_logs__logged_at__date__gte=start_of_month)),
            Value(0), output_field=IntegerField(),
        ),
        count_period=Coalesce(
            Sum("usage_logs__quantity", filter=period_filter if (d_from or d_to) else Q(pk__isnull=True)),
            Value(0), output_field=IntegerField(),
        ),
    )

    q = None
    if form.is_valid():
        q = form.cleaned_data.get("q")
        status = form.cleaned_data.get("status")
        if status == "active":
            qs = qs.filter(is_active=True)
        elif status == "inactive":
            qs = qs.filter(is_active=False)

    is_fuzzy_match = False
    if q and q.strip():
        results_list, is_fuzzy_match = fuzzy_filter_and_rank(qs, q, ["name", "code"])
    else:
        results_list = list(qs.order_by("name"))

    return form, results_list, date_from_str, date_to_str, period, is_fuzzy_match


def _paginate(request, qs, page_size=REPORT_PAGE_SIZE):
    paginator = Paginator(qs, page_size)
    return paginator.get_page(request.GET.get("page", 1))


def _querystring_without_page(request):
    params = request.GET.copy()
    params.pop("page", None)
    return params.urlencode()


def _parse_date(s):
    if not s:
        return None
    try:
        return dt.strptime(s, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _report_type_from_request(request):
    raw_type = request.GET.get("type")
    return raw_type if raw_type in ("stock", "usage") else "employee"


@login_required
def reports(request):
    report_type = _report_type_from_request(request)
    base_qs = _querystring_without_page(request)
    if "type=" not in base_qs:
        base_qs = f"{base_qs}&type={report_type}" if base_qs else f"type={report_type}"

    month_choices = _generate_month_choices()

    if report_type == "stock":
        form, qs, date_from_str, date_to_str, period = _filtered_stock_queryset(request.GET)
        total_added = qs.aggregate(total=Sum("quantity_added"))["total"] or 0
        page_obj = _paginate(request, qs)
        context = {
            "active_nav": "reports",
            "report_type": "stock",
            "form": form,
            "page_obj": page_obj,
            "results": page_obj.object_list,
            "result_count": qs.count(),
            "total_items_count": Item.objects.count(),
            "total_added": total_added,
            "base_qs": base_qs,
            "date_from": date_from_str,
            "date_to": date_to_str,
            "period": period,
            "has_custom_period": bool(date_from_str or date_to_str),
            "month_choices": month_choices,
        }
    elif report_type == "employee":
        form, results_list, date_from_str, date_to_str, period, is_fuzzy_match = _employee_summary_queryset(request.GET)
        page_obj = _paginate(request, results_list)
        context = {
            "active_nav": "reports",
            "report_type": "employee",
            "form": form,
            "page_obj": page_obj,
            "results": page_obj.object_list,
            "result_count": len(results_list),
            "total_employees_count": Employee.objects.count(),
            "base_qs": base_qs,
            "date_from": date_from_str,
            "date_to": date_to_str,
            "period": period,
            "has_custom_period": bool(date_from_str or date_to_str),
            "is_fuzzy_match": is_fuzzy_match,
            "month_choices": month_choices,
        }
    else:
        form, qs = _filtered_usage_queryset(request.GET)
        total_qty = qs.aggregate(total=Sum("quantity"))["total"] or 0
        unique_employees = qs.values("employee").distinct().count()
        page_obj = _paginate(request, qs)
        context = {
            "active_nav": "reports",
            "report_type": "usage",
            "form": form,
            "page_obj": page_obj,
            "results": page_obj.object_list,
            "result_count": qs.count(),
            "total_qty": total_qty,
            "unique_employees": unique_employees,
            "base_qs": base_qs,
            "month_choices": month_choices,
        }

    return render(request, "tracker/reports.html", context)


@login_required
def reports_employee_detail(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    logs = UsageLog.objects.filter(employee=employee).select_related("item").order_by("-logged_at")

    date_from = _parse_date(request.GET.get("date_from"))
    date_to = _parse_date(request.GET.get("date_to"))
    if date_from:
        logs = logs.filter(logged_at__date__gte=date_from)
    if date_to:
        logs = logs.filter(logged_at__date__lte=date_to)

    page_obj = _paginate(request, logs)
    base_qs = _querystring_without_page(request)
    return render(
        request,
        "tracker/reports_employee_detail.html",
        {
            "active_nav": "reports",
            "employee": employee,
            "page_obj": page_obj,
            "results": page_obj.object_list,
            "result_count": logs.count(),
            "base_qs": base_qs,
            "date_from": request.GET.get("date_from", ""),
            "date_to": request.GET.get("date_to", ""),
        },
    )


@login_required
def reports_export_csv(request):
    report_type = _report_type_from_request(request)
    response = HttpResponse(content_type="text/csv")

    if report_type == "stock":
        _, qs, _, _, _ = _filtered_stock_queryset(request.GET)
        response["Content-Disposition"] = 'attachment; filename="stock_history.csv"'
        writer = csv.writer(response)
        writer.writerow(["Date/Time", "Item", "Quantity Added", "Updated By"])
        for su in qs:
            writer.writerow([
                timezone.localtime(su.updated_at).strftime("%Y-%m-%d %H:%M"),
                su.item.name,
                su.quantity_added,
                su.updated_by.username if su.updated_by else "",
            ])
    elif report_type == "employee":
        _, results_list, _, _, _, _ = _employee_summary_queryset(request.GET)
        response["Content-Disposition"] = 'attachment; filename="employee_summary.csv"'
        writer = csv.writer(response)
        writer.writerow(["Employee", "Code", "Status", "Today", "This Week", "This Month", "Filtered Period Total"])
        for emp in results_list:
            writer.writerow([
                emp.name, emp.code, "Active" if emp.is_active else "Inactive",
                emp.count_today, emp.count_week, emp.count_month, emp.count_period,
            ])
    else:
        _, qs = _filtered_usage_queryset(request.GET)
        response["Content-Disposition"] = 'attachment; filename="usage_log.csv"'
        writer = csv.writer(response)
        writer.writerow(["Date/Time", "Employee", "Employee Code", "Item", "Quantity", "Logged By"])
        for log in qs:
            writer.writerow([
                timezone.localtime(log.logged_at).strftime("%Y-%m-%d %H:%M"),
                log.employee.name,
                log.employee.code,
                log.item.name,
                log.quantity,
                log.logged_by.username if log.logged_by else "",
            ])

    return response


@login_required
def reports_export_xlsx(request):
    report_type = _report_type_from_request(request)

    wb = Workbook()
    ws = wb.active
    header_font = Font(bold=True)

    if report_type == "stock":
        _, qs, _, _, _ = _filtered_stock_queryset(request.GET)
        ws.title = "Stock History"
        headers = ["Date/Time", "Item", "Quantity Added", "Updated By"]
        ws.append(headers)
        for su in qs:
            ws.append([
                timezone.localtime(su.updated_at).strftime("%Y-%m-%d %H:%M"),
                su.item.name,
                su.quantity_added,
                su.updated_by.username if su.updated_by else "",
            ])
        filename = "stock_history.xlsx"
    elif report_type == "employee":
        _, results_list, _, _, _, _ = _employee_summary_queryset(request.GET)
        ws.title = "Employee Summary"
        headers = ["Employee", "Code", "Status", "Today", "This Week", "This Month", "Filtered Period Total"]
        ws.append(headers)
        for emp in results_list:
            ws.append([
                emp.name, emp.code, "Active" if emp.is_active else "Inactive",
                emp.count_today, emp.count_week, emp.count_month, emp.count_period,
            ])
        filename = "employee_summary.xlsx"
    else:
        _, qs = _filtered_usage_queryset(request.GET)
        ws.title = "Usage Log"
        headers = ["Date/Time", "Employee", "Employee Code", "Item", "Quantity", "Logged By"]
        ws.append(headers)
        for log in qs:
            ws.append([
                timezone.localtime(log.logged_at).strftime("%Y-%m-%d %H:%M"),
                log.employee.name,
                log.employee.code,
                log.item.name,
                log.quantity,
                log.logged_by.username if log.logged_by else "",
            ])
        filename = "usage_log.xlsx"

    for col_idx in range(1, len(headers) + 1):
        ws.cell(row=1, column=col_idx).font = header_font

    for column_cells in ws.columns:
        length = max((len(str(cell.value)) if cell.value is not None else 0) for cell in column_cells)
        ws.column_dimensions[column_cells[0].column_letter].width = min(max(length + 2, 10), 40)

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    response = HttpResponse(
        buffer.read(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
