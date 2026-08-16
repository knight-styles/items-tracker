from django.contrib import messages
from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ..forms import StockUpdateForm
from ..models import AppSettings, Item, StockUpdate
from ..permissions import supervisor_required


@supervisor_required
def supervisor_stock(request):
    items = Item.objects.filter(is_active=True).order_by("name")
    low_stock_threshold = AppSettings.load().low_stock_threshold
    return render(
        request,
        "tracker/supervisor/stock.html",
        {"items": items, "active_nav": "stock", "low_stock_threshold": low_stock_threshold, "form": StockUpdateForm()},
    )


@supervisor_required
@require_POST
def supervisor_stock_update(request, pk):
    item = get_object_or_404(Item, pk=pk, is_active=True)
    form = StockUpdateForm(request.POST)
    if form.is_valid():
        qty = form.cleaned_data["quantity_added"]
        with transaction.atomic():
            Item.objects.filter(pk=item.pk).update(current_stock=F("current_stock") + qty)
            StockUpdate.objects.create(item=item, quantity_added=qty, updated_by=request.user)
        messages.success(request, f"Added {qty} to '{item.name}' stock.")
    else:
        messages.error(request, "Please enter a valid quantity (a positive whole number).")
    return redirect("supervisor_stock")
