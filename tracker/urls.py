from django.urls import path

from . import views

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("", views.dashboard_redirect, name="dashboard_redirect"),

    # Admin - Dashboard
    path("admin-panel/dashboard/", views.admin_dashboard, name="admin_dashboard"),

    # Admin - Employees
    path("admin-panel/employees/", views.admin_employees, name="admin_employees"),
    path("admin-panel/employees/add/", views.admin_employee_add, name="admin_employee_add"),
    path("admin-panel/employees/import/", views.admin_employee_import, name="admin_employee_import"),
    path("admin-panel/employees/bulk-deactivate/", views.admin_employee_bulk_deactivate, name="admin_employee_bulk_deactivate"),
    path("admin-panel/employees/<int:pk>/edit/", views.admin_employee_edit, name="admin_employee_edit"),
    path("admin-panel/employees/<int:pk>/toggle-active/", views.admin_employee_toggle_active, name="admin_employee_toggle_active"),
    path("admin-panel/employees/<int:pk>/delete/", views.admin_employee_delete, name="admin_employee_delete"),

    # Admin - Items
    path("admin-panel/items/", views.admin_items, name="admin_items"),
    path("admin-panel/items/add/", views.admin_item_add, name="admin_item_add"),
    path("admin-panel/items/import/", views.admin_item_import, name="admin_item_import"),
    path("admin-panel/items/<int:pk>/edit/", views.admin_item_edit, name="admin_item_edit"),
    path("admin-panel/items/<int:pk>/toggle-active/", views.admin_item_toggle_active, name="admin_item_toggle_active"),
    path("admin-panel/items/<int:pk>/delete/", views.admin_item_delete, name="admin_item_delete"),

    # Admin - Users (Supervisor account management)
    path("admin-panel/users/", views.admin_users, name="admin_users"),
    path("admin-panel/users/add/", views.admin_user_add, name="admin_user_add"),
    path("admin-panel/users/<int:pk>/edit/", views.admin_user_edit, name="admin_user_edit"),
    path("admin-panel/users/<int:pk>/toggle-active/", views.admin_user_toggle_active, name="admin_user_toggle_active"),
    path("admin-panel/users/<int:pk>/reset-password/", views.admin_user_reset_password, name="admin_user_reset_password"),

    # Admin - Settings
    path("admin-panel/settings/", views.admin_settings, name="admin_settings"),
    path("admin-panel/audit-log/", views.admin_audit_log, name="admin_audit_log"),

    # Supervisor - Log
    path("log/", views.supervisor_log, name="supervisor_log"),
    path("log/employee-search/", views.supervisor_log_employee_search, name="supervisor_log_employee_search"),
    path("log/item-options/", views.supervisor_log_item_options, name="supervisor_log_item_options"),
    path("log/submit/", views.supervisor_log_submit, name="supervisor_log_submit"),
    path("log/bulk-allocate/", views.supervisor_bulk_periodic_allocate, name="supervisor_bulk_periodic_allocate"),

    # Supervisor - Add Employee (add + edit only, no delete)
    path("add-employee/", views.supervisor_add_employee, name="supervisor_add_employee"),
    path("add-employee/add/", views.supervisor_employee_add, name="supervisor_employee_add"),
    path("add-employee/<int:pk>/edit/", views.supervisor_employee_edit, name="supervisor_employee_edit"),

    # Supervisor - Stock
    path("stock/", views.supervisor_stock, name="supervisor_stock"),
    path("stock/<int:pk>/update/", views.supervisor_stock_update, name="supervisor_stock_update"),

    # Shared
    path("reports/", views.reports, name="reports"),
    path("reports/employee/<int:pk>/", views.reports_employee_detail, name="reports_employee_detail"),
    path("reports/export/", views.reports_export_csv, name="reports_export_csv"),
    path("reports/export/xlsx/", views.reports_export_xlsx, name="reports_export_xlsx"),

    # Employee Profile Card
    path("employee/<int:pk>/profile/", views.employee_profile, name="employee_profile"),
]
