import csv
import io

from django.contrib import messages
from django.db.models import ProtectedError, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ..audit import log_audit
from ..forms import BulkDeactivateForm, CSVImportForm, EmployeeForm, EmployeeSearchForm
from ..models import Employee
from ..permissions import admin_required, supervisor_required


# --------------------------------------------------------------------------
# Shared list/form helpers (Admin: full CRUD with soft-delete/deactivate.
#                            Supervisor: add + edit only, no delete/deactivate.)
# --------------------------------------------------------------------------

def _employee_list(request, *, mode):
    form = EmployeeSearchForm(request.GET or None)
    employees = Employee.objects.all()

    if form.is_valid():
        q = form.cleaned_data.get("q")
        status = form.cleaned_data.get("status")
        if q:
            employees = employees.filter(Q(name__icontains=q) | Q(code__icontains=q))
        if status == "active":
            employees = employees.filter(is_active=True)
        elif status == "inactive":
            employees = employees.filter(is_active=False)

    context = {
        "employees": employees,
        "form": form,
        "active_nav": "employees" if mode == "admin" else "add_employee",
        "mode": mode,
    }
    template = "tracker/admin/employees_list.html" if mode == "admin" else "tracker/supervisor/employees_list.html"
    return render(request, template, context)


def _employee_form(request, *, mode, employee=None):
    is_edit = employee is not None
    if request.method == "POST":
        form = EmployeeForm(request.POST, instance=employee)
        if form.is_valid():
            obj = form.save(commit=False)
            if is_edit:
                obj.updated_by = request.user
            else:
                obj.created_by = request.user
                obj.updated_by = request.user
            if mode == "supervisor":
                if is_edit:
                    obj.is_active = employee.is_active
                else:
                    obj.is_active = True
            obj.save()
            messages.success(request, f"Employee '{obj.name}' {'updated' if is_edit else 'added'} successfully.")
            return redirect("admin_employees" if mode == "admin" else "supervisor_add_employee")
    else:
        form = EmployeeForm(instance=employee)
        if mode == "supervisor":
            form.fields.pop("is_active", None)

    context = {
        "form": form,
        "is_edit": is_edit,
        "employee": employee,
        "active_nav": "employees" if mode == "admin" else "add_employee",
        "mode": mode,
    }
    template = "tracker/admin/employee_form.html" if mode == "admin" else "tracker/supervisor/employee_form.html"
    return render(request, template, context)


@admin_required
def admin_employees(request):
    return _employee_list(request, mode="admin")


@admin_required
def admin_employee_add(request):
    return _employee_form(request, mode="admin")


@admin_required
def admin_employee_edit(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    return _employee_form(request, mode="admin", employee=employee)


@admin_required
@require_POST
def admin_employee_toggle_active(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    employee.is_active = not employee.is_active
    employee.updated_by = request.user
    employee.save()
    action = "activate" if employee.is_active else "deactivate"
    log_audit(request.user, action, "Employee", employee.name, details=f"code={employee.code}")
    messages.success(request, f"Employee '{employee.name}' {'activated' if employee.is_active else 'deactivated'}.")
    return redirect("admin_employees")


@admin_required
@require_POST
def admin_employee_delete(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    try:
        name, code = employee.name, employee.code
        employee.delete()
        log_audit(request.user, "delete", "Employee", name, details=f"code={code}")
        messages.success(request, f"Employee '{name}' deleted.")
    except ProtectedError:
        messages.error(
            request,
            f"Can't delete '{employee.name}' -- usage history exists for this employee. "
            "Deactivate instead to hide them from the Log tab.",
        )
    return redirect("admin_employees")


@supervisor_required
def supervisor_add_employee(request):
    return _employee_list(request, mode="supervisor")


@supervisor_required
def supervisor_employee_add(request):
    return _employee_form(request, mode="supervisor")


@supervisor_required
def supervisor_employee_edit(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    return _employee_form(request, mode="supervisor", employee=employee)


# --------------------------------------------------------------------------
# Bulk import (Admin only)
# --------------------------------------------------------------------------

def _import_employees_csv(file_obj, user, update_existing=False):
    created, updated, skipped = 0, 0, 0
    errors = []
    try:
        decoded = file_obj.read().decode("utf-8-sig")
    except UnicodeDecodeError:
        return {"created": 0, "updated": 0, "skipped": 0, "errors": ["Could not read file -- please upload a plain CSV file."]}

    reader = csv.DictReader(io.StringIO(decoded))
    if not reader.fieldnames:
        return {"created": 0, "updated": 0, "skipped": 0, "errors": ["CSV appears empty or malformed."]}

    field_map = {h.strip().lower(): h for h in reader.fieldnames}
    if "name" not in field_map or "code" not in field_map:
        return {"created": 0, "updated": 0, "skipped": 0, "errors": ['CSV must have "name" and "code" columns.']}

    for i, row in enumerate(reader, start=2):  # row 1 is the header
        name = (row.get(field_map["name"]) or "").strip()
        code = (row.get(field_map["code"]) or "").strip()
        if not name or not code:
            errors.append(f"Row {i}: missing name or code -- skipped.")
            continue

        existing = Employee.objects.filter(code=code).first()
        if existing:
            if update_existing:
                existing.name = name
                existing.updated_by = user
                existing.save()
                updated += 1
            else:
                skipped += 1
            continue

        Employee.objects.create(name=name, code=code, created_by=user, updated_by=user)
        created += 1

    return {"created": created, "updated": updated, "skipped": skipped, "errors": errors}


@admin_required
def admin_employee_import(request):
    result = None
    if request.method == "POST":
        form = CSVImportForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded = form.cleaned_data["csv_file"]
            update_existing = form.cleaned_data["update_existing"]
            if not uploaded.name.lower().endswith(".csv"):
                messages.error(request, "Please upload a .csv file.")
            else:
                result = _import_employees_csv(uploaded, request.user, update_existing=update_existing)
                if result["created"] or result["updated"]:
                    log_audit(
                        request.user, "bulk_import", "Employee", uploaded.name,
                        details=f"created={result['created']} updated={result['updated']} skipped={result['skipped']}",
                    )
                    messages.success(
                        request,
                        f"Imported {result['created']} new, updated {result['updated']} employee(s).",
                    )
    else:
        form = CSVImportForm()

    return render(
        request,
        "tracker/admin/csv_import.html",
        {
            "form": form,
            "result": result,
            "active_nav": "employees",
            "title": "Import Employees",
            "back_url_name": "admin_employees",
            "format_instructions": [
                '"name" -- employee full name (required)',
                '"code" -- unique employee ID/code (required)',
            ],
            "example": "name,code\nRamesh Kumar,EMP-101\nSuresh Patel,EMP-102",
            "note": "By default, rows with a code that already exists are skipped. Check \"Update existing records\" to update their name instead.",
        },
    )


def _bulk_deactivate_employees_csv(file_obj, user):
    deactivated, not_found, already_inactive = 0, 0, 0
    errors = []
    try:
        decoded = file_obj.read().decode("utf-8-sig")
    except UnicodeDecodeError:
        return {"deactivated": 0, "not_found": 0, "already_inactive": 0, "errors": ["Could not read file -- please upload a plain CSV file."]}

    reader = csv.DictReader(io.StringIO(decoded))
    if not reader.fieldnames:
        return {"deactivated": 0, "not_found": 0, "already_inactive": 0, "errors": ["CSV appears empty or malformed."]}

    field_map = {h.strip().lower(): h for h in reader.fieldnames}
    if "code" not in field_map:
        return {"deactivated": 0, "not_found": 0, "already_inactive": 0, "errors": ['CSV must have a "code" column.']}

    for i, row in enumerate(reader, start=2):
        code = (row.get(field_map["code"]) or "").strip()
        if not code:
            errors.append(f"Row {i}: missing code -- skipped.")
            continue
        emp = Employee.objects.filter(code=code).first()
        if not emp:
            not_found += 1
            errors.append(f"Row {i}: no employee found with code '{code}'.")
            continue
        if not emp.is_active:
            already_inactive += 1
            continue
        emp.is_active = False
        emp.updated_by = user
        emp.save()
        deactivated += 1
        log_audit(user, "bulk_deactivate", "Employee", emp.name, details=f"code={emp.code}")

    return {"deactivated": deactivated, "not_found": not_found, "already_inactive": already_inactive, "errors": errors}


@admin_required
def admin_employee_bulk_deactivate(request):
    result = None
    if request.method == "POST":
        form = BulkDeactivateForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded = form.cleaned_data["csv_file"]
            if not uploaded.name.lower().endswith(".csv"):
                messages.error(request, "Please upload a .csv file.")
            else:
                result = _bulk_deactivate_employees_csv(uploaded, request.user)
                if result["deactivated"]:
                    messages.success(request, f"Deactivated {result['deactivated']} employee(s).")
    else:
        form = BulkDeactivateForm()

    return render(
        request,
        "tracker/admin/employee_bulk_deactivate.html",
        {"form": form, "result": result, "active_nav": "employees"},
    )
