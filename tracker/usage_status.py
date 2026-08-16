"""
Computes the display status of an item for a given employee on the Log tab:
  - 'today'   -> employee took this item within the current reset window (red)
  - 'period'  -> employee took this item within the configured period, but
                 the reset window has already passed (blue)
  - 'normal'  -> no recent usage, or never taken (default color)

Two reset modes (set in AppSettings):
  - 'fixed_time'  -> the "day" resets at a fixed clock time (e.g. 20:00).
                      Anything logged since the most recent occurrence of
                      that time counts as "today".
  - 'hours_after' -> each log has its own personal reset window: N hours
                      after that specific log, it stops counting as "today".
"""
from datetime import timedelta

from django.utils import timezone


def most_recent_reset_moment(reset_time, reference):
    """
    Return the most recent datetime (<= reference) at which reset_time
    occurred, treating reset_time as local wall-clock time.

    `reference` is typically a UTC-aware datetime (e.g. from timezone.now()).
    We convert it to local time first so the hour/minute we splice in match
    what the Admin actually picked in the Settings UI -- a plain <input
    type="time"> has no timezone concept, so "20:00" always means 8pm in
    the project's TIME_ZONE (see settings.py), not 8pm UTC.
    """
    local_reference = timezone.localtime(reference)
    candidate = local_reference.replace(
        hour=reset_time.hour, minute=reset_time.minute, second=0, microsecond=0
    )
    if candidate > local_reference:
        candidate -= timedelta(days=1)
    return candidate


def compute_item_status(last_log_at, app_settings, *, now=None):
    """
    last_log_at: datetime of the employee's most recent log for this item, or None.
    app_settings: an AppSettings instance.
    Returns one of 'normal', 'today', 'period'.
    """
    if last_log_at is None:
        return "normal"

    now = now or timezone.now()

    if app_settings.reset_mode == app_settings.ResetMode.HOURS_AFTER:
        reset_at = last_log_at + timedelta(hours=app_settings.reset_hours)
        if now < reset_at:
            return "today"
    else:  # FIXED_TIME
        cutoff = most_recent_reset_moment(app_settings.reset_time, now)
        if last_log_at >= cutoff:
            return "today"

    period_start = now - timedelta(days=app_settings.period_days)
    if last_log_at >= period_start:
        return "period"

    return "normal"
