from .auth import login_view, logout_view, dashboard_redirect
from .dashboard import admin_dashboard
from .employees import (
    admin_employees,
    admin_employee_add,
    admin_employee_edit,
    admin_employee_toggle_active,
    admin_employee_delete,
    admin_employee_import,
    admin_employee_bulk_deactivate,
    supervisor_add_employee,
    supervisor_employee_add,
    supervisor_employee_edit,
)
from .items import (
    admin_items,
    admin_item_add,
    admin_item_edit,
    admin_item_toggle_active,
    admin_item_delete,
    admin_item_import,
)
from .users import (
    admin_users,
    admin_user_add,
    admin_user_edit,
    admin_user_toggle_active,
    admin_user_reset_password,
)
from .settings import admin_settings, admin_audit_log
from .log import (
    supervisor_log,
    supervisor_log_employee_search,
    supervisor_log_item_options,
    supervisor_log_submit,
    supervisor_bulk_periodic_allocate,
)
from .stock import supervisor_stock, supervisor_stock_update
from .reports import (
    reports,
    reports_employee_detail,
    reports_export_csv,
    reports_export_xlsx,
)

__all__ = [
    "login_view", "logout_view", "dashboard_redirect",
    "admin_dashboard",
    "admin_employees", "admin_employee_add", "admin_employee_edit",
    "admin_employee_toggle_active", "admin_employee_delete", "admin_employee_import",
    "admin_employee_bulk_deactivate",
    "supervisor_add_employee", "supervisor_employee_add", "supervisor_employee_edit",
    "admin_items", "admin_item_add", "admin_item_edit",
    "admin_item_toggle_active", "admin_item_delete", "admin_item_import",
    "admin_users", "admin_user_add", "admin_user_edit", "admin_user_toggle_active",
    "admin_user_reset_password",
    "admin_settings", "admin_audit_log",
    "supervisor_log", "supervisor_log_employee_search", "supervisor_log_item_options",
    "supervisor_log_submit", "supervisor_bulk_periodic_allocate",
    "supervisor_stock", "supervisor_stock_update",
    "reports", "reports_employee_detail", "reports_export_csv", "reports_export_xlsx",
]
