"""
Role-based access control helpers.

Usage on function views:
    @admin_required
    def my_view(request): ...

    @supervisor_required
    def my_view(request): ...

Usage on class-based views:
    class MyView(AdminRequiredMixin, View): ...
    class MyView(SupervisorRequiredMixin, View): ...
"""
from functools import wraps

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect


def admin_required(view_func):
    """Allows only authenticated Admin (or superuser) users."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if not request.user.is_admin():
            messages.error(request, "You don't have permission to access that page.")
            return redirect("dashboard_redirect")
        return view_func(request, *args, **kwargs)
    return _wrapped


def supervisor_required(view_func):
    """Allows authenticated Supervisors and Admins."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if not (request.user.is_supervisor() or request.user.is_admin()):
            messages.error(request, "You don't have permission to access that page.")
            return redirect("dashboard_redirect")
        return view_func(request, *args, **kwargs)
    return _wrapped


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_admin()

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            messages.error(self.request, "You don't have permission to access that page.")
            return redirect("dashboard_redirect")
        return super().handle_no_permission()


class SupervisorRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_supervisor() or self.request.user.is_admin()

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            messages.error(self.request, "You don't have permission to access that page.")
            return redirect("dashboard_redirect")
        return super().handle_no_permission()
