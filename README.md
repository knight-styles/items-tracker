# Safety Item Tracker

A minimal Django app for tracking safety item usage by employees over time.
There's no limit on how much an employee can take -- the app just counts it,
tracks stock, and gives Admin/Supervisor visibility into who took what and
when.

**This is the complete application** -- all core phases plus a full round
of production-readiness, UX, reporting, and code-health improvements.

## Roles

- **Admin** -- full CRUD on Employees and Items, manages Supervisor accounts
  (including password resets), configures Settings, views Dashboard,
  Reports, and the Audit Log. Admin accounts are managed via `/django-admin/`
  only (kept out of the in-app UI for safety).
- **Supervisor** -- logs item usage against employees, adds new employees
  (add/edit only, no delete), views/adds stock, views Reports.

Admin can also reach Supervisor-only URLs directly (Log, Add Employee,
Stock) even though those tabs aren't in the Admin sidebar -- Admin is
treated as a superset of Supervisor permissions throughout.

## Feature summary

**Dashboard (Admin)** -- active employee/item/supervisor counts, items
logged today and within the configured period, low-stock item count, a
7-day usage trend (simple CSS bar chart, no charting library), and a
recent-activity feed.

**Employees (Admin)** -- search/filter, add, edit, deactivate/reactivate,
delete (blocked with a clear message if usage history exists -- deactivate
instead). Bulk import via CSV (create-only or "update existing" mode) and
bulk deactivate via a CSV of employee codes. Every record shows who
created/last edited it and when.

**Items (Admin)** -- same CRUD pattern, plus a stock column with a
low-stock highlight driven by the Settings threshold, and CSV bulk import.

**Users (Admin)** -- create and deactivate Supervisor accounts, reset a
Supervisor's password directly (no email flow -- share the new password
with them securely), with an audit trail of who created whom.

**Settings (Admin)** -- the period (in days) an item stays highlighted after
being taken, the reset mode (fixed clock time each day, or N hours after
each assignment -- the irrelevant field auto-hides based on your choice),
colors for the "today" and "period" highlights, and the low-stock
threshold. Links through to the Audit Log.

**Audit Log (Admin)** -- a filterable, paginated, chronological record of
deletes, deactivations, password resets, settings changes, and bulk
import/deactivate operations -- who did what and when.

**Add Employee (Supervisor)** -- search existing employees, add new ones,
edit existing ones. No delete/deactivate -- that's Admin-only.

**Log (Supervisor)** -- type-ahead employee search; once selected, up to 5
item dropdowns (1 required, 4 optional via "add another item") where an
item already picked in one dropdown disappears from the others. Each option
is colored live based on that employee's usage history: red if within the
current reset window, blue if within the period, default otherwise.
Logging is never blocked -- an employee can take the same item repeatedly
in a day; stock just keeps decrementing (and is allowed to go negative,
never shown as "out of stock"). After submitting, the same employee is
pre-selected on reload so logging another item for them is fast.

**Stock (Supervisor)** -- view current stock per item with a low-stock
highlight, and add received stock via a popup dialog. Every addition is
recorded (who, how much, when) for the audit trail.

**Reports (shared)** -- three tabs:
- **Usage Log** -- the raw log list, date-range/employee/item filters, sorting
- **By Employee** -- one row per employee showing item counts taken today,
  this week (calendar week, Monday start), and this month (calendar month
  to date). Search by name/code, filter by active/inactive. Click an
  employee's name for a simple two-column history (Date, Item Name) of
  everything they've taken, with its own date-range filter and a Print
  button (print-friendly CSS hides the nav/header/footer).
- **Stock History** -- stock additions, date-range/item filters, sorting

All three tabs have pagination (25 rows per page) and "Export CSV" /
"Export Excel" buttons that respect the current filters and export the
*full* filtered result set (not just the current page).

## Security & production readiness

- Login is rate-limited: 5 failed attempts locks that username out for
  ~15 minutes (tracked via Django's cache framework). A locked-out account
  can't log in even with the correct password until the window passes.
- `SECRET_KEY`, `DEBUG`, and `ALLOWED_HOSTS` are all read from environment
  variables (`DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`),
  with safe local-dev defaults baked in so `manage.py runserver` still
  works out of the box.
- When `DJANGO_DEBUG=False`, HSTS, secure cookies, and SSL redirect are
  automatically enabled (the SSL redirect can be disabled independently via
  `DJANGO_SECURE_SSL_REDIRECT=False` if your host's proxy setup needs it).

## Architecture notes

- **`tracker/views/`** is a package, not a single file -- split into
  `auth.py`, `dashboard.py`, `employees.py`, `items.py`, `users.py`,
  `settings.py`, `log.py`, `stock.py`, and `reports.py`. `tracker/urls.py`
  is unaffected (`from . import views` still works via `views/__init__.py`
  re-exporting everything).
- **`tracker/tests/`** is a real automated test suite (89 tests) covering
  auth/rate-limiting, permissions, Employee/Item CRUD, Log submission and
  validation, the today/period/normal status-color logic (including the
  non-midnight reset boundary edge case), Reports filtering/pagination,
  CSV/Excel export, bulk import, bulk deactivate, and the audit trail. Run
  with `python manage.py test tracker`.
- `tracker/usage_status.py` holds the pure status-calculation logic
  (`compute_item_status`), independently unit-tested. **Note:** the
  "fixed time" reset boundary is computed in the project's local timezone
  (`Asia/Kolkata`), not UTC -- this was a real bug caught by the test suite
  during development (a reset configured for "20:00" was firing at 20:00
  UTC, i.e. 1:30am local time, until fixed).
- `AppSettings.load()` always returns a properly-typed instance, even on
  the very first call on a brand-new install before Admin has ever saved
  Settings -- also a real bug caught by testing (a freshly-created row's
  fields carried raw Python defaults like the string `"00:00"` instead of
  a real `datetime.time`, which would have crashed the Log tab).
- `tracker/audit.py` provides `log_audit()`, a small helper used throughout
  the views package to write `AuditLog` entries; it never raises, so an
  audit-logging hiccup can't break the request that triggered it.
- The Log tab uses vanilla JS (no framework) talking to two small JSON
  endpoints (`/log/employee-search/`, `/log/item-options/`) plus a normal
  form POST to `/log/submit/`.
- The Stock tab's "Update Stock" popup uses a native `<dialog>` element --
  no JS framework or modal library.
- All user-supplied IDs are validated before being used in querysets (a
  malformed or empty ID returns a clean error instead of a 500).
- Reports, CSV export, and Excel export all share the same filtering helper
  functions so the on-screen results and both exported files are always
  consistent with each other -- exports always cover the full filtered set,
  independent of which page you're viewing on screen.

## Running locally

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Visit `http://127.0.0.1:8000/`.

## Running the test suite

```bash
python manage.py test tracker
```

## Test accounts (seeded for review — remove before real deployment)

| Username | Password       | Role       |
|----------|----------------|------------|
| admin1   | AdminPass123!  | Admin      |
| super1   | SuperPass123!  | Supervisor |

Seed data also includes 2 sample employees, 3 sample items, a default
Settings row (7-day period, fixed reset at midnight, low-stock threshold 5),
and a handful of sample usage/stock entries so Reports and the Dashboard
aren't empty on first load.

## Project structure

```
safety_tracker/
├── manage.py
├── requirements.txt
├── safety_tracker/        # project settings (env-var driven), root urls.py
├── tracker/
│   ├── models.py           # User, Employee, Item, AppSettings, UsageLog, StockUpdate, AuditLog
│   ├── usage_status.py      # today/period/normal status calculation
│   ├── audit.py             # log_audit() helper
│   ├── forms.py             # all forms, including report filters and CSV import
│   ├── views/                # split by area -- see Architecture notes above
│   │   ├── auth.py, dashboard.py, employees.py, items.py, users.py,
│   │   └── settings.py, log.py, stock.py, reports.py
│   ├── tests/                 # 89 automated tests, split by area
│   ├── urls.py
│   ├── permissions.py       # role-based access control
│   └── admin.py
├── templates/tracker/
│   ├── base.html
│   ├── login.html
│   ├── reports.html          # shared Usage Log / By Employee / Stock History tabs
│   ├── reports_employee_detail.html
│   ├── admin/                 # dashboard, employees, items, users, settings,
│   │                            audit_log, csv_import, employee_bulk_deactivate,
│   │                            user_reset_password
│   └── supervisor/            # add-employee, log, stock
└── static/css/base.css
```

## Deploying to PythonAnywhere

1. Push this project to a GitHub repo (excluding `db.sqlite3` for a clean
   production database).
2. On PythonAnywhere: open a Bash console, `git clone` the repo.
3. Create a virtualenv, `pip install -r requirements.txt`.
4. In the **Web** tab, create a new web app → **Manual configuration** → your
   Python version → point the WSGI file at `safety_tracker.wsgi.application`
   and set the virtualenv path.
5. Set `Static files` mapping: URL `/static/` → path to `staticfiles/`
   (after running `python manage.py collectstatic`).
6. Before going live, set these environment variables (PythonAnywhere's
   Web tab has an "Environment variables" section, or set them in the WSGI
   config file before the Django import):
   - `DJANGO_SECRET_KEY` -- a fresh, random value (don't reuse the dev one)
   - `DJANGO_DEBUG=False`
   - `DJANGO_ALLOWED_HOSTS=yourapp.pythonanywhere.com`
   - If you hit SSL-redirect issues behind PythonAnywhere's proxy, add
     `DJANGO_SECURE_SSL_REDIRECT=False`
7. Run `python manage.py migrate` and `python manage.py createsuperuser` in
   a PythonAnywhere console (this becomes your first Admin).

## Possible future enhancements (not built)

- Multi-process-safe rate limiting (current implementation uses Django's
  default in-memory cache, which is per-process -- fine for a single web
  worker; switch to a shared backend like Redis if you scale to multiple)
- Email-based password reset flow for Supervisors (currently Admin sets a
  new password directly and shares it out-of-band)
- PostgreSQL migration guide for higher-concurrency deployments
