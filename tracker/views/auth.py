from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from ..models import User

LOGIN_ATTEMPT_LIMIT = 5
LOGIN_LOCKOUT_SECONDS = 15 * 60


def _attempts_cache_key(username):
    return f"login_attempts:{username.strip().lower()}"


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard_redirect")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        cache_key = _attempts_cache_key(username) if username else None

        if cache_key and cache.get(cache_key, 0) >= LOGIN_ATTEMPT_LIMIT:
            messages.error(
                request,
                "Too many failed login attempts for this account. Please wait about 15 minutes and try again.",
            )
            return render(request, "tracker/login.html")

        # Django's default auth backend silently rejects inactive users inside
        # authenticate() (returns None), so we check active status ourselves
        # first to give a clearer message than a generic "invalid credentials".
        existing = User.objects.filter(username=username).first() if username else None
        if existing and not existing.is_active and existing.check_password(password):
            messages.error(request, "This account has been deactivated.")
            return render(request, "tracker/login.html")

        user = authenticate(request, username=username, password=password)
        if user is not None:
            if cache_key:
                cache.delete(cache_key)
            login(request, user)
            return redirect("dashboard_redirect")
        else:
            if cache_key:
                attempts = cache.get(cache_key, 0) + 1
                cache.set(cache_key, attempts, LOGIN_LOCKOUT_SECONDS)
            messages.error(request, "Invalid username or password.")

    return render(request, "tracker/login.html")


@login_required
@require_POST
def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def dashboard_redirect(request):
    """
    Landing route after login. Sends Admins to the dashboard and
    Supervisors straight to the Log tab (their primary daily task).
    """
    if request.user.is_admin():
        return redirect("admin_dashboard")
    return redirect("supervisor_log")
