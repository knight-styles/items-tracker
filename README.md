# Safety Item Tracker

[![Django Version](https://img.shields.io/badge/Django-5.2.16-092E20?logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Python Version](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![PWA Ready](https://img.shields.io/badge/PWA-Ready-5A0FC8?logo=pwa&logoColor=white)](https://web.dev/progressive-web-apps/)
[![Automated Tests](https://img.shields.io/badge/Tests-131%20Passed-10B981?logo=pytest&logoColor=white)](https://docs.djangoproject.com/en/5.2/topics/testing/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

An enterprise-grade, production-ready Django web application for tracking employee personal protective equipment (PPE) and safety item issuance over time. The application enables industrial facilities, warehouses, and operations teams to monitor safety gear consumption, manage inventory levels, enforce compliance policies, detect equipment wear anomalies, and generate audit-ready Excel and CSV reports.

---

## Table of Contents

- [Key Capabilities & Highlights](#key-capabilities--highlights)
- [User Roles & Access Control](#user-roles--access-control)
- [Comprehensive Feature Walkthrough](#comprehensive-feature-walkthrough)
  - [1. Executive Intelligence Dashboard](#1-executive-intelligence-dashboard-admin)
  - [2. Interactive Equipment Usage Logging](#2-interactive-equipment-usage-logging-supervisor--admin)
  - [3. Bulk Periodic Safety Kit Allocation](#3-bulk-periodic-safety-kit-allocation-supervisor--admin)
  - [4. Employee 360° Profile & Equipment Cards](#4-employee-360-profile--equipment-cards-shared)
  - [5. Employee Management & Bulk Operations](#5-employee-management--bulk-operations-admin--supervisor)
  - [6. Safety Equipment & Stock Management](#6-safety-equipment--stock-management-admin--supervisor)
  - [7. Supervisor User Management & Password Resets](#7-supervisor-user-management--password-resets-admin)
  - [8. Application Settings & Policy Engine](#8-application-settings--policy-engine-admin)
  - [9. System-Wide Audit Logging](#9-system-wide-audit-logging-admin)
  - [10. Analytics, Reports & Dual-Format Exports](#10-analytics-reports--dual-format-exports-shared)
  - [11. Progressive Web App (PWA) & Offline Capabilities](#11-progressive-web-app-pwa--offline-capabilities)
- [Technical Architecture & Engineering Design](#technical-architecture--engineering-design)
  - [Data Models & Schema Relationships](#data-models--schema-relationships)
  - [Timezone-Aware Reset Engine](#timezone-aware-reset-engine)
  - [Damerau-Levenshtein Typo-Tolerant Search](#damerau-levenshtein-typo-tolerant-search)
  - [Modular View Architecture](#modular-view-architecture)
  - [Database Optimization & Query Efficiency](#database-optimization--query-efficiency)
- [Security Hardening & Production Safeguards](#security-hardening--production-safeguards)
- [Installation & Local Setup](#installation--local-setup)
- [Automated Test Suite](#automated-test-suite)
- [Production Deployment Guide](#production-deployment-guide)
  - [Deployment to PythonAnywhere](#deployment-to-pythonanywhere)
  - [Deployment to Linux / Cloud VPS](#deployment-to-linux--cloud-vps)
- [Project Directory Structure](#project-directory-structure)

---

## Key Capabilities & Highlights

- **Visual Equipment Selection Grid**: Interactive cards displaying custom vector SVG illustrations or uploaded photos for each safety gear type with live color-coded usage status badges (*Taken Today*, *Within Period*, *Available*).
- **Typo-Tolerant Damerau-Levenshtein Fuzzy Search**: Real-time employee lookup that intelligently handles spelling mistakes, transpositions, and character variations across names and codes.
- **Bulk Periodic Safety Kit Allocation**: 1-click batch issuance of a complete safety kit (1 piece of every active item) to all active employees with atomic stock updating and a configurable cooldown timer to prevent accidental duplicate allotments.
- **Employee 360° Profile & Equipment Cards**: Dedicated employee history card (`/employee/<id>/profile/`) with KPI metrics (All-Time, Month, Week, Today), item-by-item issuance breakdown, filterable history table, and print-optimized CSS layout.
- **Executive Analytics & Loss Prevention Dashboard**: Real-time workforce compliance metrics, 4-month historical trend graphs with percentage growth indicators, 7-day peak demand analysis, stock inventory health distributions, and a high-frequency replacement anomaly monitor.
- **Dual-Format Full-Dataset Exports**: Export filtered datasets directly to beautifully styled Excel Workbooks (`.xlsx` via `openpyxl` with auto-sized columns and bold headers) and CSV Spreadsheets (`.csv`).
- **Comprehensive Audit Trail**: Automatically records sensitive events (creations, deactivations, deletions, password resets, setting modifications, and bulk operations) in an immutable chronological log.
- **Progressive Web App (PWA) & Offline Readiness**: Full PWA support with Web App Manifest, Service Worker caching, offline fallback mode, online/offline status banners, and mobile drawer navigation.
- **Zero External JS Framework Overhead**: Fast, lightweight vanilla JavaScript frontend combined with semantic HTML5 and a tailored Vanilla CSS design system.
- **Non-Blocking Operation**: Issuing safety gear is never artificially blocked — stock count decrements continuously and is allowed to go negative if usage temporarily exceeds recorded inventory.

---

## User Roles & Access Control

The application implements strict Role-Based Access Control (RBAC) separating administrative governance from floor operations:

| Feature / Action | Admin | Supervisor | Notes |
| :--- | :---: | :---: | :--- |
| **Executive Dashboard** | Yes | Direct Link | Real-time KPIs, trends, stock distribution & anomaly detection |
| **Log Equipment Usage** | Yes | Yes | Visual grid, live status highlights, multi-item batch selection |
| **Bulk Periodic Allocation** | Yes | Yes | Issues full kit to all active employees; protected by cooldown timer |
| **Employee 360° Profile** | Yes | Yes | KPI strip, equipment cards, paginated history, print mode |
| **Add / Edit Employees** | Yes | Yes | Supervisors can create and update names/codes |
| **Deactivate / Delete Employees** | Yes | No | Delete is blocked if usage history exists (deactivate instead) |
| **Bulk CSV Employee Import** | Yes | No | Supports create-only or update-existing modes |
| **Bulk Employee Deactivation** | Yes | No | Batch deactivation via CSV of employee codes |
| **Add / Edit Safety Items & Images** | Yes | No | Upload item images or use smart vector SVG fallbacks |
| **View Stock & Receive Additions** | Yes | Yes | Supervisor stock table with native `<dialog>` update modal |
| **Manage Supervisor Accounts** | Yes | No | Create, edit, toggle active status, direct password reset |
| **Configure App Settings** | Yes | No | Highlight duration, reset modes, colors, thresholds, cooldowns |
| **View Audit Trail Log** | Yes | No | Chronological record of administrative and sensitive actions |
| **View & Export Reports** | Yes | Yes | Filterable Usage Log, By Employee, Stock History (Excel/CSV) |
| **Django Built-in Admin** | Superuser | No | Available at `/django-admin/` for superuser management |

> **Note**: Admin permissions are a superset of Supervisor permissions throughout the application. Admins can access all supervisor routes directly.

---

## Comprehensive Feature Walkthrough

### 1. Executive Intelligence Dashboard (Admin)
Accessible at `/admin-panel/dashboard/`, the Executive Dashboard provides an instant operational overview:

- **Workforce & Inventory KPIs**:
  - **Active Employees**: Total active workforce count and compliance tracking percentage.
  - **Total Stock Units**: Total available safety units across all active item categories.
  - **Issued in 30 Days**: Volume of safety gear distributed in the trailing 30-day window.
  - **Estimated Financial & Loss Savings**: Calculates dollar/rupee savings from controlled tracking (estimating a 25% reduction in unrecorded loss/waste).
  - **Low Stock & Out-of-Stock Warnings**: Instant visual alerts when inventory drops below the configured reorder threshold.
- **Month-over-Month Issue Volume**: 4-month historical bar graph displaying monthly demand counts and percentage change (+/-%) between consecutive months.
- **7-Day Daily Demand Chart**: Pure CSS bar chart showing daily equipment demand with automatic peak-day detection.
- **Stock Inventory Distribution & Health**:
  - Breakdown of inventory into *Healthy* (green), *Low Stock* (amber), and *Out of Stock* (rose) percentages.
  - Progress bar distribution showing relative inventory shares per safety item category.
- **Top Equipment Demand Share**: Ranks the top 5 most frequently requested PPE items over the past 30 days.
- **High-Frequency Replacement Anomaly Monitor**:
  - Automatically flags potential equipment loss or excessive turnover (detects employees receiving 2 or more safety reallocations within a 14-day window).
  - Lists employee details, re-allocated item summaries, and total units issued.
  - Computes an overall **Asset Lifecycle Integrity Score** (0% - 100%).

---

### 2. Interactive Equipment Usage Logging (Supervisor / Admin)
Accessible at `/log/`, this is the daily workflow interface for issuing safety equipment to workers:

- **Search-as-You-Type Employee Lookup**:
  - Type-ahead search field matching employee names or unique employee codes.
  - Typo-tolerant fuzzy search matches misspellings (e.g. typing `"employyee"` or `"saftey"`).
  - Selected employee is displayed in a dedicated bar with an avatar, employee code, a direct link to their **360° Profile Card**, and a "Change Employee" button.
- **Visual Equipment Selection Grid**:
  - Replaces traditional dropdowns with responsive, image-supported equipment cards.
  - Cards dynamically display uploaded item photos or vector illustrations for helmets, goggles, gloves, vests, boots, respirators, face shields, harnesses, and first aid kits.
  - Integrated in-grid quick filter search bar (`#item-filter-input`) to filter items instantly.
  - "Select All" and "Clear" quick action buttons with a dynamic selection counter badge (`X selected`).
- **Live Status Color Indicators**:
  - Each item card reflects that specific employee's usage history in real-time:
    - **Taken Today** (default Red `#dc2626`): The employee has already received this item within the current reset window.
    - **Taken in Period** (default Blue `#2563eb`): The employee received this item within the configured period window (e.g. 7 days), but outside today's reset window.
    - **Available / Normal** (default Green `#10b981`): No recent usage recorded.
- **Multi-Item Batch Submission**:
  - Supervisors can select multiple distinct safety items and submit them in a single action.
  - Backend validation prevents duplicate item selections in a single submission.
  - Records all usage entries and decrements stock in an atomic database transaction.
  - After submission, the page reloads with the same employee pre-selected for rapid logging.

---

### 3. Bulk Periodic Safety Kit Allocation (Supervisor / Admin)
For routine operations (e.g., monthly safety kit distribution), supervisors can issue equipment to the entire workforce with one click:

- **1-Click Execution**: Issues 1 unit of every active safety item to all active employees simultaneously.
- **Optimized Batch Processing**: Inserts usage records using Django's `bulk_create` (1,000-row batching) and executes single-query inventory updates per item.
- **Cooldown Protection Engine**:
  - Configured via `AppSettings.bulk_issue_cooldown_days` (default 30 days).
  - When cooldown is active, the bulk issue button is gracefully disabled with a countdown indicator: `Bulk Allotment Cooldown Active (Xd)`.
  - Backend validation strictly rejects attempts to trigger allocation during active cooldown.
- **Modal Confirmation Dialog**: Native `<dialog>` confirmation displaying allotment summary, employee count, and inventory impact.

---

### 4. Employee 360° Profile & Equipment Cards (Shared)
Accessible at `/employee/<id>/profile/` (linked from the Log tab, Reports, and employee lists):

- **Hero Profile Header**: Gradient banner displaying employee initials, full name, employee code badge, active/inactive badge, enrollment date, and action buttons.
- **4-Metric KPI Strip**: Real-time aggregated statistics calculated in a single query:
  - *Total All-Time* safety units received
  - *This Month* safety units received
  - *This Week* safety units received
  - *Today* safety units received
- **Equipment Issued Grid**: Visual cards for every safety item type ever issued to the employee, showing item thumbnail, total times issued, total quantity received, last issued date, and live status badges (*Issued Today* / *Within Period*).
- **Usage History Table**: Paginated chronological history table showing Date & Time, Item name badge, Quantity, and Logged By supervisor username.
- **Date Range Filters**: Filter history logs by *From Date* and *To Date*.
- **Print-Friendly Mode**: Built-in `@media print` styling removes headers, sidebars, and navigation buttons for clean physical printing or PDF exporting.

---

### 5. Employee Management & Bulk Operations (Admin / Supervisor)
Accessible at `/admin-panel/employees/` (Admin) and `/add-employee/` (Supervisor):

- **Employee Search & Filtering**: Filter by search query (name/code) and status (*All*, *Active*, *Inactive*).
- **Add / Edit Employee**: Form fields for employee name, unique employee code, and active status.
- **Safe Delete Protection**: Deleting an employee with existing usage records is blocked with a descriptive error message (`models.PROTECT`), directing the administrator to deactivate the record instead.
- **Soft Deactivation Toggle**: 1-click activation/deactivation toggle with automatic audit logging.
- **Bulk CSV Import (`/admin-panel/employees/import/`)**:
  - Upload a standard `.csv` file containing `name` and `code` columns.
  - Option to "Update existing records" to modify existing employee names, or skip existing codes.
- **Bulk CSV Deactivation (`/admin-panel/employees/bulk-deactivate/`)**:
  - Upload a `.csv` file with a `code` column to deactivate departing personnel in bulk without losing historical compliance data.

---

### 6. Safety Equipment & Stock Management (Admin / Supervisor)
Accessible at `/admin-panel/items/` (Admin) and `/stock/` (Supervisor):

- **Item Management**: Add and edit safety item names, initial inventory stock, active status, and custom equipment images (`Item.image` stored in `media/item_images/`).
- **Low-Stock Highlighting**: Dynamic visual badges highlight items with current stock at or below `low_stock_threshold`.
- **Delete Protection**: Deleting items with existing usage logs is blocked by database constraints.
- **Bulk CSV Import (`/admin-panel/items/import/`)**: Upload CSV with `name` and optional `current_stock` columns.
- **Supervisor Stock Control (`/stock/`)**:
  - Table showing active safety items, current stock quantities, and low-stock alerts.
  - Native `<dialog>` modal popup allowing supervisors to record incoming stock deliveries.
  - All stock additions are recorded in the `StockUpdate` model with quantity, timestamp, and user tracking.

---

### 7. Supervisor User Management & Password Resets (Admin)
Accessible at `/admin-panel/users/`:

- **Account Administration**: Create and edit supervisor login credentials (username, first name, last name, password).
- **Active Status Toggle**: Deactivate supervisor accounts instantly to revoke access.
- **Direct Password Reset (`/admin-panel/users/<id>/reset-password/`)**:
  - Admins can set a new password directly for supervisors without requiring an external SMTP email server.
  - Validates password strength and logs the reset event to the audit trail.

---

### 8. Application Settings & Policy Engine (Admin)
Accessible at `/admin-panel/settings/`:

- **Period Window (`period_days`)**: Configures the number of days (default 7) an item remains highlighted as "within period" after issuance.
- **Reset Mode Configuration**:
  - **Fixed Time (`fixed_time`)**: Daily reset occurs at a fixed local wall-clock time (e.g. `00:00` midnight or `20:00` shift change in `Asia/Kolkata` timezone).
  - **Hours After (`hours_after`)**: Individual reset window expiring N hours (e.g. 20 hours) after each specific item assignment.
- **Custom Status Colors**: Native HTML5 color pickers for `color_today` (default `#dc2626`) and `color_period` (default `#2563eb`).
- **Low Stock Threshold**: Threshold number of units (default 5) below which safety items are flagged.
- **Bulk Issue Cooldown**: Number of days (default 30) before the Bulk Periodic Allocation feature can be executed again.
- **Singleton Resilience**: `AppSettings.load()` ensures settings are always typed and available even on fresh installations.

---

### 9. System-Wide Audit Logging (Admin)
Accessible at `/admin-panel/audit-log/`:

- Centralized chronological record of all security and governance actions across the app:
  - Account creations, deactivations, activations, and password resets.
  - Employee and item additions, edits, deletions, and active toggles.
  - Bulk CSV import and bulk deactivation summaries.
  - Settings modifications (tracking the exact fields changed).
- Action filter dropdown to inspect specific events (e.g. `delete`, `bulk_import`, `password_reset`, `settings_update`).
- Paginated (30 entries per page) with full details and actor metadata.
- Exception-safe `log_audit()` helper ensures auditing errors never interrupt core user workflows.

---

### 10. Analytics, Reports & Dual-Format Exports (Shared)
Accessible at `/reports/`:

- **Three Dedicated Reporting Tabs**:
  1. **By Employee**: Summary matrix displaying item counts taken *Today*, *This Week*, *This Month*, and *Filtered Range Total*.
     - Quick date preset buttons (*This Week*, *Current Month*).
     - 12-month historical dropdown selector.
     - Typo-tolerant fuzzy search input for employee names and codes.
     - Direct click through to the Employee 360° Profile Card.
  2. **Stock History**: Log of all stock additions with date range filters, item dropdown filter, and sorting.
  3. **Usage Log**: Transaction-by-transaction log of all safety equipment issued with date range, employee, and item filters.
- **Universal Interactive Table Sorting**: Clickable table column headers with ascending/descending indicators.
- **Export Settings & Preview Modal**:
  - Native `<dialog>` modal showing export scope preview (record count and date range).
  - **Excel Workbook (`.xlsx`)**: Generated via `openpyxl` with styled bold headers and auto-fitted column widths.
  - **CSV Spreadsheet (`.csv`)**: Clean CSV export formatted with localized timestamps.
  - **Full-Dataset Export**: Exports cover the entire filtered dataset across all pages, not just the active page.

---

### 11. Progressive Web App (PWA) & Offline Capabilities

- **Web App Manifest (`/static/manifest.json`)**: Configures standalone display mode, theme colors (`#4f46e5`), high-resolution maskable app icons (192x192 & 512x512), and app shortcuts for *Log Usage*, *Stock Control*, and *Reports*.
- **Service Worker (`/sw.js`)**: Registered at root scope (`/`), caching static CSS, JavaScript, icons, and shell layouts.
- **Offline Fallback (`/static/offline.html`)**: Automatically presented when a user navigates to an uncached page while disconnected.
- **Online / Offline Status Banner**: Real-time event listener displays a banner when internet connectivity is lost.
- **In-App PWA Install Prompt**: Header button triggers the browser's native `beforeinstallprompt` to install the app on mobile or desktop devices.
- **Responsive Mobile Navigation**: Collapsible sidebar drawer with backdrop overlay for smartphones and tablets.

---

## Technical Architecture & Engineering Design

```
safety_tracker/
├── manage.py
├── requirements.txt
├── safety_tracker/                  # Django project configuration
│   ├── settings.py                  # Env-driven settings & security hardening
│   ├── urls.py                      # Root URL router & service worker registration
│   ├── wsgi.py                      # Production WSGI application
│   └── asgi.py
├── tracker/                         # Core application package
│   ├── models.py                    # User, Employee, Item, AppSettings, UsageLog, StockUpdate, AuditLog
│   ├── usage_status.py              # Timezone-aware status calculation logic
│   ├── search_utils.py              # Damerau-Levenshtein fuzzy matching algorithm
│   ├── audit.py                     # Exception-safe log_audit() helper
│   ├── forms.py                     # Form definitions & validation rules
│   ├── permissions.py               # Role-based access decorators (@admin_required, @supervisor_required)
│   ├── admin.py                     # Built-in Django admin registration
│   ├── urls.py                      # Application route definitions
│   ├── views/                       # Modular view package
│   │   ├── auth.py                  # Login rate-limiting & authentication
│   │   ├── dashboard.py             # Executive dashboard KPIs & anomaly detection
│   │   ├── log.py                   # Usage logging & bulk periodic allocation
│   │   ├── employee_profile.py      # Employee 360° profile card
│   │   ├── employees.py             # Employee CRUD & bulk CSV operations
│   │   ├── items.py                 # Safety item CRUD & bulk CSV import
│   │   ├── stock.py                 # Supervisor stock inventory management
│   │   ├── users.py                 # Supervisor user management & password resets
│   │   ├── settings.py              # App settings form & audit log view
│   │   └── reports.py               # Reports, analytics & Excel/CSV export engine
│   └── tests/                       # 131 automated unit and integration tests
├── templates/tracker/               # UI Templates
│   ├── base.html                    # Base layout, sidebar, PWA tags, table sorting
│   ├── login.html                   # Styled login page
│   ├── employee_profile.html        # 360° Employee profile & history card
│   ├── reports.html                 # Reports tabs & export modal
│   ├── reports_employee_detail.html # Printable simple report view
│   ├── admin/                       # Admin dashboard, forms, audit log, CSV import
│   └── supervisor/                  # Log usage grid, stock control, employee forms
└── static/                          # Static assets
    ├── css/base.css                 # Vanilla CSS design system
    ├── sw.js                        # Service worker script
    ├── manifest.json                # PWA manifest
    ├── offline.html                 # Offline fallback page
    └── images/                      # PWA icons & equipment item images
```

### Data Models & Schema Relationships

```mermaid
erDiagram
    User ||--o{ Employee : "creates/updates"
    User ||--o{ Item : "creates/updates"
    User ||--o{ UsageLog : "logs"
    User ||--o{ StockUpdate : "updates"
    User ||--o{ AuditLog : "acts"
    Employee ||--o{ UsageLog : "receives"
    Item ||--o{ UsageLog : "issued in"
    Item ||--o{ StockUpdate : "replenished in"

    User {
        int id PK
        string username
        string role "admin | supervisor"
        fk created_by
    }
    Employee {
        int id PK
        string name
        string code UK
        boolean is_active
        datetime created_at
    }
    Item {
        int id PK
        string name UK
        int current_stock
        string image
        boolean is_active
    }
    AppSettings {
        int id PK "singleton (pk=1)"
        int period_days
        string reset_mode "fixed_time | hours_after"
        time reset_time
        int reset_hours
        string color_today
        string color_period
        int low_stock_threshold
        int bulk_issue_cooldown_days
        datetime last_bulk_issue_at
    }
    UsageLog {
        int id PK
        fk employee_id
        fk item_id
        int quantity
        fk logged_by
        datetime logged_at
    }
    StockUpdate {
        int id PK
        fk item_id
        int quantity_added
        fk updated_by
        datetime updated_at
    }
    AuditLog {
        int id PK
        fk actor_id
        string action
        string target_type
        string target_repr
        text details
        datetime created_at
    }
```

### Timezone-Aware Reset Engine
The status calculation engine (`tracker/usage_status.py`) evaluates item status against the project's local timezone (`Asia/Kolkata`):
- For `fixed_time` reset mode, wall-clock time is converted in the local timezone so that setting a reset at `"20:00"` resets precisely at 8:00 PM local time regardless of UTC offset.
- For `hours_after` mode, the expiration threshold is computed per assignment timestamp (`last_log_at + N hours`).

### Damerau-Levenshtein Typo-Tolerant Search
Implemented in `tracker/search_utils.py`, the search engine supports:
- Full exact match and exact word match (scores 1000.0 and 800.0).
- Prefix matching (score 500.0+).
- Substring matching (score 300.0).
- Damerau-Levenshtein edit distance calculations allowing up to 1 edit for 4-7 character words, and 2 edits for longer terms.

### Database Optimization & Query Efficiency
- **N+1 Query Elimination**: The item status endpoint (`/log/item-options/`) fetches all recent logs for the employee in a single query with dictionary mapping.
- **Range-Indexed Lookups**: Date filters use `logged_at__gte` and `logged_at__lt` ranges rather than `__year`/`__month` transformations to enable database index utilization on `db_index=True`.
- **Atomic Bulk Operations**: Bulk periodic allotments use single-query stock decrements (`F('current_stock') - N`) and batched `UsageLog` inserts.

---

## Security Hardening & Production Safeguards

- **Rate-Limited Authentication**: Tracks failed login attempts per username in Django's cache framework. Exceeding 5 failed attempts triggers an automatic 15-minute account lockout.
- **Explicit Inactive Account Feedback**: Distinguishes between deactivated user accounts and incorrect passwords.
- **Strict Environment Configuration**:
  - `DJANGO_SECRET_KEY`: Fails startup immediately if the default insecure key is used in production (`DEBUG=False`).
  - `DJANGO_DEBUG`: Defaults to `True` for development, easily set to `False` via environment variable.
  - `DJANGO_ALLOWED_HOSTS`: Configured via comma-separated domain list.
- **Production SSL & Cookie Hardening**: When `DEBUG=False`, automatically enforces `SECURE_HSTS_SECONDS`, `SESSION_COOKIE_SECURE = True`, `CSRF_COOKIE_SECURE = True`, and `SECURE_SSL_REDIRECT = True`.
- **Referential Integrity**: All `UsageLog` foreign keys use `on_delete=models.PROTECT` to prevent accidental loss of historical compliance logs.

---

## Installation & Local Setup

### Prerequisites
- Python 3.12+ (or 3.10+)
- `pip` and `virtualenv`

### Quickstart

1. **Clone the repository**:
   ```bash
   git clone <repo-url>
   cd safety_tracker
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Apply database migrations**:
   ```bash
   python manage.py migrate
   ```

5. **Start the local development server**:
   ```bash
   python manage.py runserver
   ```

6. **Access the application**:
   Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) in your web browser.

---

### Seed Test Accounts (Development & Evaluation)

| Username | Password | Role | Primary Landing Page |
| :--- | :--- | :--- | :--- |
| `admin1` | `AdminPass123!` | **Admin** | `/admin-panel/dashboard/` |
| `super1` | `SuperPass123!` | **Supervisor** | `/log/` |

> [!WARNING]
> Change or delete these test accounts before deploying to any public or production environment.

---

## Automated Test Suite

The project includes an automated test suite comprising **131 unit and integration tests** verifying all layers of the application.

### Running Tests

Execute the complete test suite:
```bash
./venv/bin/python manage.py test tracker
```

### Test Coverage Breakdown

| Test Module | Focus Area |
| :--- | :--- |
| `test_auth.py` | Login authentication, rate-limiting lockout, deactivated user handling |
| `test_permissions.py` | Role-based view access, supervisor restrictions, admin superset routes |
| `test_employees_items.py` | Employee/Item CRUD, active toggles, delete protection, image uploads |
| `test_log.py` | Log submission, grid selector, multi-item batch, prefilling, negative stock |
| `test_usage_status.py` | Timezone-aware status engine (Today vs Period vs Normal), reset modes |
| `test_employee_profile.py` | 360° Profile card, KPI aggregation, equipment cards, history pagination |
| `test_fuzzy_search.py` | Damerau-Levenshtein distance, typo tolerance, prefix/token ranking |
| `test_bulk_and_audit.py` | CSV import/deactivation, bulk periodic allotment, audit log capture |
| `test_reports.py` | By Employee summary, Stock History, Usage Log, pagination, XLSX/CSV export |
| `test_pwa.py` | PWA manifest, service worker at `/sw.js`, offline page, install tags |
| `test_migrations.py` | Validates that all model schema changes have corresponding migration files |

---

## Production Deployment Guide

### Deployment to PythonAnywhere

1. Push your code to a GitHub repository (exclude `db.sqlite3` and `media/` via `.gitignore`).
2. On PythonAnywhere: open a **Bash console** and clone your repository:
   ```bash
   git clone https://github.com/<your-user>/safety_tracker.git
   cd safety_tracker
   ```
3. Create a virtual environment and install dependencies:
   ```bash
   mkvirtualenv --python=/usr/bin/python3.12 safety-env
   pip install -r requirements.txt
   ```
4. In the PythonAnywhere **Web** tab:
   - Create a new web app using **Manual configuration** with Python 3.12.
   - Set the **Virtualenv path**: `/home/<username>/.virtualenvs/safety-env`.
   - Edit the **WSGI configuration file**:
     ```python
     import os
     import sys

     path = '/home/<username>/safety_tracker'
     if path not in sys.path:
         sys.path.append(path)

     os.environ['DJANGO_SETTINGS_MODULE'] = 'safety_tracker.settings'
     os.environ['DJANGO_DEBUG'] = 'False'
     os.environ['DJANGO_SECRET_KEY'] = 'your-secure-random-secret-key'
     os.environ['DJANGO_ALLOWED_HOSTS'] = '<username>.pythonanywhere.com'
     os.environ['DJANGO_SECURE_SSL_REDIRECT'] = 'False'  # Handled by PythonAnywhere proxy

     from django.core.wsgi import get_wsgi_application
     application = get_wsgi_application()
     ```
5. Configure **Static & Media File Mappings** in the Web tab:
   - URL `/static/` &rarr; Directory `/home/<username>/safety_tracker/staticfiles`
   - URL `/media/` &rarr; Directory `/home/<username>/safety_tracker/media`
6. In the Bash console, collect static files, run migrations, and create your superuser:
   ```bash
   python manage.py collectstatic --noinput
   python manage.py migrate
   python manage.py createsuperuser
   ```
7. Click **Reload <username>.pythonanywhere.com** in the Web tab.

---

### Deployment to Linux / Cloud VPS

When deploying to Ubuntu/Debian servers with **Gunicorn** and **Nginx**:

1. **Environment Variables**: Set the following in `/etc/environment` or your systemd service file:
   ```ini
   DJANGO_SECRET_KEY=your-generated-production-key
   DJANGO_DEBUG=False
   DJANGO_ALLOWED_HOSTS=safety.yourdomain.com
   DJANGO_SECURE_SSL_REDIRECT=True
   ```
2. **Nginx Configuration**:
   ```nginx
   server {
       listen 80;
       server_name safety.yourdomain.com;
       return 301 https://$host$request_uri;
   }

   server {
       listen 443 ssl http2;
       server_name safety.yourdomain.com;

       ssl_certificate /etc/letsencrypt/live/safety.yourdomain.com/fullchain.pem;
       ssl_certificate_key /etc/letsencrypt/live/safety.yourdomain.com/privkey.pem;

       location /static/ {
           alias /var/www/safety_tracker/staticfiles/;
       }

       location /media/ {
           alias /var/www/safety_tracker/media/;
       }

       location /sw.js {
           alias /var/www/safety_tracker/static/sw.js;
           add_header Cache-Control "no-cache";
       }

       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```
3. **Multi-Worker Cache Backend**:
   For multi-worker Gunicorn deployments across multiple processes or nodes, configure a shared Redis cache in `settings.py`:
   ```python
   CACHES = {
       "default": {
           "BACKEND": "django.core.cache.backends.redis.RedisCache",
           "LOCATION": "redis://127.0.0.1:6379/1",
       }
   }
   ```

---

## Project Directory Structure

```
safety_tracker/
├── db.sqlite3                                 # SQLite database
├── manage.py                                  # Django management runner
├── requirements.txt                           # Python project dependencies
├── media/                                     # User-uploaded equipment media
│   └── item_images/
├── safety_tracker/                            # Django project settings
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── tracker/                                   # Application source code
│   ├── admin.py
│   ├── apps.py
│   ├── audit.py                               # Audit helper (log_audit)
│   ├── forms.py                               # Forms & search filters
│   ├── models.py                              # Core DB models & AppSettings
│   ├── permissions.py                         # RBAC decorators
│   ├── search_utils.py                        # Typo-tolerant search algorithm
│   ├── usage_status.py                        # Status calculation logic
│   ├── urls.py                                # Application routes
│   ├── migrations/                            # Schema migrations
│   │   ├── 0001_initial.py
│   │   ├── 0002_employee_item.py
│   │   ├── 0003_appsettings_usagelog.py
│   │   ├── 0004_stockupdate.py
│   │   ├── 0005_auditlog.py
│   │   ├── 0006_alter_usagelog_logged_at.py
│   │   ├── 0007_appsettings_bulk_issue_cooldown_days_and_more.py
│   │   └── 0008_item_image.py
│   ├── views/                                 # Modular view package
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── dashboard.py
│   │   ├── employee_profile.py
│   │   ├── employees.py
│   │   ├── items.py
│   │   ├── log.py
│   │   ├── reports.py
│   │   ├── settings.py
│   │   ├── stock.py
│   │   └── users.py
│   └── tests/                                 # 131 automated tests
│       ├── __init__.py
│       ├── base.py
│       ├── test_auth.py
│       ├── test_bulk_and_audit.py
│       ├── test_employee_profile.py
│       ├── test_employees_items.py
│       ├── test_fuzzy_search.py
│       ├── test_log.py
│       ├── test_migrations.py
│       ├── test_permissions.py
│       ├── test_pwa.py
│       ├── test_reports.py
│       └── test_usage_status.py
├── templates/tracker/                         # HTML Templates
│   ├── base.html                              # App shell & layout
│   ├── login.html                             # Login view
│   ├── reports.html                           # Analytics & reports tabs
│   ├── reports_employee_detail.html           # Simple employee detail
│   ├── employee_profile.html                  # 360° Employee profile
│   ├── admin/
│   │   ├── audit_log.html
│   │   ├── csv_import.html
│   │   ├── dashboard.html
│   │   ├── employee_bulk_deactivate.html
│   │   ├── employee_form.html
│   │   ├── employees_list.html
│   │   ├── item_form.html
│   │   ├── items_list.html
│   │   ├── settings_form.html
│   │   ├── user_form.html
│   │   ├── user_reset_password.html
│   │   └── users_list.html
│   └── supervisor/
│       ├── employee_form.html
│       ├── employees_list.html
│       ├── log.html                           # Equipment usage grid
│       └── stock.html                         # Stock inventory & update modal
└── static/                                    # Frontend assets
    ├── manifest.json                          # PWA manifest
    ├── offline.html                           # Offline fallback page
    ├── sw.js                                  # PWA service worker
    ├── css/
    │   └── base.css                           # Design system & tokens
    └── images/
        ├── pwa/
        │   ├── icon-192.png
        │   └── icon-512.png
        └── items/
            ├── boots.jpg
            ├── gloves.jpg
            ├── goggles.jpg
            ├── helmet.jpg
            └── vest.jpg
```

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
