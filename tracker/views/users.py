from django.contrib import messages
from django.contrib.auth.forms import SetPasswordForm
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ..audit import log_audit
from ..forms import SupervisorCreateForm, SupervisorEditForm
from ..models import User
from ..permissions import admin_required


@admin_required
def admin_users(request):
    users = User.objects.filter(role=User.Role.SUPERVISOR, is_superuser=False).order_by("username")
    return render(request, "tracker/admin/users_list.html", {"users": users, "active_nav": "users"})


@admin_required
def admin_user_add(request):
    if request.method == "POST":
        form = SupervisorCreateForm(request.POST)
        if form.is_valid():
            user = form.save(created_by=request.user)
            log_audit(request.user, "create", "User", user.username)
            messages.success(request, f"Supervisor account '{user.username}' created.")
            return redirect("admin_users")
    else:
        form = SupervisorCreateForm()
    return render(request, "tracker/admin/user_form.html", {"form": form, "is_edit": False, "active_nav": "users"})


@admin_required
def admin_user_edit(request, pk):
    user_obj = get_object_or_404(User, pk=pk, role=User.Role.SUPERVISOR, is_superuser=False)
    if request.method == "POST":
        form = SupervisorEditForm(request.POST, instance=user_obj)
        if form.is_valid():
            form.save()
            messages.success(request, f"Supervisor '{user_obj.username}' updated.")
            return redirect("admin_users")
    else:
        form = SupervisorEditForm(instance=user_obj)
    return render(
        request,
        "tracker/admin/user_form.html",
        {"form": form, "is_edit": True, "user_obj": user_obj, "active_nav": "users"},
    )


@admin_required
@require_POST
def admin_user_toggle_active(request, pk):
    user_obj = get_object_or_404(User, pk=pk, role=User.Role.SUPERVISOR, is_superuser=False)
    user_obj.is_active = not user_obj.is_active
    user_obj.save()
    action = "activate" if user_obj.is_active else "deactivate"
    log_audit(request.user, action, "User", user_obj.username)
    messages.success(
        request, f"Supervisor '{user_obj.username}' {'activated' if user_obj.is_active else 'deactivated'}."
    )
    return redirect("admin_users")


@admin_required
def admin_user_reset_password(request, pk):
    user_obj = get_object_or_404(User, pk=pk, role=User.Role.SUPERVISOR, is_superuser=False)
    if request.method == "POST":
        form = SetPasswordForm(user_obj, request.POST)
        if form.is_valid():
            form.save()
            log_audit(request.user, "password_reset", "User", user_obj.username)
            messages.success(
                request,
                f"Password reset for '{user_obj.username}'. Share the new password with them securely -- "
                "it won't be shown again here.",
            )
            return redirect("admin_users")
    else:
        form = SetPasswordForm(user_obj)
    return render(
        request,
        "tracker/admin/user_reset_password.html",
        {"form": form, "user_obj": user_obj, "active_nav": "users"},
    )
