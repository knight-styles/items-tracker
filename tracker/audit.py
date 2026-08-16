import logging

from .models import AuditLog

logger = logging.getLogger(__name__)


def log_audit(actor, action, target_type, target_repr, details=""):
    """
    Records a sensitive action. Never raises -- audit logging failures
    should never break the request that triggered them. Failures are
    surfaced via logging.warning() so they appear in server logs.
    """
    try:
        AuditLog.objects.create(
            actor=actor if getattr(actor, "is_authenticated", False) else None,
            action=action,
            target_type=target_type,
            target_repr=str(target_repr)[:255],
            details=details,
        )
    except Exception as exc:  # pragma: no cover
        logger.warning("AuditLog write failed [%s %s '%s']: %s", action, target_type, target_repr, exc)
