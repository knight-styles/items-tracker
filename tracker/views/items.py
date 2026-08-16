import csv
import io

from django.contrib import messages
from django.db.models import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ..audit import log_audit
from ..forms import CSVImportForm, ItemForm, ItemSearchForm
from ..models import AppSettings, Item
from ..permissions import admin_required


@admin_required
def admin_items(request):
    form = ItemSearchForm(request.GET or None)
    items = Item.objects.all()

    if form.is_valid():
        q = form.cleaned_data.get("q")
        status = form.cleaned_data.get("status")
        if q:
            items = items.filter(name__icontains=q)
        if status == "active":
            items = items.filter(is_active=True)
        elif status == "inactive":
            items = items.filter(is_active=False)

    low_stock_threshold = AppSettings.load().low_stock_threshold

    return render(
        request,
        "tracker/admin/items_list.html",
        {"items": items, "form": form, "active_nav": "items", "low_stock_threshold": low_stock_threshold},
    )


@admin_required
def admin_item_add(request):
    if request.method == "POST":
        form = ItemForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.created_by = request.user
            obj.updated_by = request.user
            obj.save()
            messages.success(request, f"Item '{obj.name}' added successfully.")
            return redirect("admin_items")
    else:
        form = ItemForm()
    return render(
        request,
        "tracker/admin/item_form.html",
        {"form": form, "is_edit": False, "active_nav": "items"},
    )


@admin_required
def admin_item_edit(request, pk):
    item = get_object_or_404(Item, pk=pk)
    if request.method == "POST":
        form = ItemForm(request.POST, instance=item)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.updated_by = request.user
            obj.save()
            messages.success(request, f"Item '{obj.name}' updated successfully.")
            return redirect("admin_items")
    else:
        form = ItemForm(instance=item)
    return render(
        request,
        "tracker/admin/item_form.html",
        {"form": form, "is_edit": True, "item": item, "active_nav": "items"},
    )


@admin_required
@require_POST
def admin_item_toggle_active(request, pk):
    item = get_object_or_404(Item, pk=pk)
    item.is_active = not item.is_active
    item.updated_by = request.user
    item.save()
    action = "activate" if item.is_active else "deactivate"
    log_audit(request.user, action, "Item", item.name)
    messages.success(request, f"Item '{item.name}' {'activated' if item.is_active else 'deactivated'}.")
    return redirect("admin_items")


@admin_required
@require_POST
def admin_item_delete(request, pk):
    item = get_object_or_404(Item, pk=pk)
    try:
        name = item.name
        item.delete()
        log_audit(request.user, "delete", "Item", name)
        messages.success(request, f"Item '{name}' deleted.")
    except ProtectedError:
        messages.error(
            request,
            f"Can't delete '{item.name}' -- usage history exists for this item. "
            "Deactivate instead to hide it from the Log tab.",
        )
    return redirect("admin_items")


# --------------------------------------------------------------------------
# Bulk import (Admin only)
# --------------------------------------------------------------------------

def _import_items_csv(file_obj, user, update_existing=False):
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
    if "name" not in field_map:
        return {"created": 0, "updated": 0, "skipped": 0, "errors": ['CSV must have a "name" column.']}
    stock_key = field_map.get("current_stock") or field_map.get("stock")

    for i, row in enumerate(reader, start=2):
        name = (row.get(field_map["name"]) or "").strip()
        if not name:
            errors.append(f"Row {i}: missing name -- skipped.")
            continue

        stock_val = None
        if stock_key:
            raw = (row.get(stock_key) or "").strip()
            if raw:
                try:
                    stock_val = int(raw)
                except ValueError:
                    errors.append(f'Row {i}: invalid stock value "{raw}" -- ignored.')

        existing = Item.objects.filter(name=name).first()
        if existing:
            if update_existing:
                if stock_val is not None:
                    existing.current_stock = stock_val
                existing.updated_by = user
                existing.save()
                updated += 1
            else:
                skipped += 1
            continue

        Item.objects.create(name=name, current_stock=stock_val if stock_val is not None else 0, created_by=user, updated_by=user)
        created += 1

    return {"created": created, "updated": updated, "skipped": skipped, "errors": errors}


@admin_required
def admin_item_import(request):
    result = None
    if request.method == "POST":
        form = CSVImportForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded = form.cleaned_data["csv_file"]
            update_existing = form.cleaned_data["update_existing"]
            if not uploaded.name.lower().endswith(".csv"):
                messages.error(request, "Please upload a .csv file.")
            else:
                result = _import_items_csv(uploaded, request.user, update_existing=update_existing)
                if result["created"] or result["updated"]:
                    log_audit(
                        request.user, "bulk_import", "Item", uploaded.name,
                        details=f"created={result['created']} updated={result['updated']} skipped={result['skipped']}",
                    )
                    messages.success(
                        request,
                        f"Imported {result['created']} new, updated {result['updated']} item(s).",
                    )
    else:
        form = CSVImportForm()

    return render(
        request,
        "tracker/admin/csv_import.html",
        {
            "form": form,
            "result": result,
            "active_nav": "items",
            "title": "Import Items",
            "back_url_name": "admin_items",
            "format_instructions": [
                '"name" -- item name, must be unique (required)',
                '"current_stock" -- starting stock quantity (optional, defaults to 0)',
            ],
            "example": "name,current_stock\nSafety Goggles,50\nEar Plugs,200",
            "note": "By default, rows whose name already exists are skipped. Check \"Update existing records\" to update their stock instead.",
        },
    )
