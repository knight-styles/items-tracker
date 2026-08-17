from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import AppSettings, Employee, Item, User


class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ["name", "code", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "e.g. Ramesh Kumar"}),
            "code": forms.TextInput(attrs={"placeholder": "e.g. EMP-1024"}),
        }


class EmployeeSearchForm(forms.Form):
    q = forms.CharField(required=False, label="Search")
    status = forms.ChoiceField(
        required=False,
        choices=[("", "All"), ("active", "Active"), ("inactive", "Inactive")],
    )


class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = ["name", "current_stock", "image", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "e.g. Safety Goggles"}),
            "image": forms.FileInput(attrs={"accept": "image/*"}),
        }


class ItemSearchForm(forms.Form):
    q = forms.CharField(required=False, label="Search")
    status = forms.ChoiceField(
        required=False,
        choices=[("", "All"), ("active", "Active"), ("inactive", "Inactive")],
    )


class SupervisorCreateForm(UserCreationForm):
    first_name = forms.CharField(required=True)
    last_name = forms.CharField(required=False)

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "password1", "password2"]

    def save(self, commit=True, created_by=None):
        user = super().save(commit=False)
        user.role = User.Role.SUPERVISOR
        user.created_by = created_by
        if commit:
            user.save()
        return user


class SettingsForm(forms.ModelForm):
    class Meta:
        model = AppSettings
        fields = [
            "period_days",
            "reset_mode",
            "reset_time",
            "reset_hours",
            "color_today",
            "color_period",
            "low_stock_threshold",
            "bulk_issue_cooldown_days",
        ]
        widgets = {
            "reset_time": forms.TimeInput(attrs={"type": "time"}),
            "color_today": forms.TextInput(attrs={"type": "color"}),
            "color_period": forms.TextInput(attrs={"type": "color"}),
        }


class SupervisorEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name"]  # is_active managed via dedicated toggle endpoint (audited)


class StockUpdateForm(forms.Form):
    quantity_added = forms.IntegerField(min_value=1, label="Quantity to add")


class UsageReportFilterForm(forms.Form):
    date_from = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    date_to = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    employee = forms.ModelChoiceField(queryset=Employee.objects.all().order_by("name"), required=False)
    item = forms.ModelChoiceField(queryset=Item.objects.all().order_by("name"), required=False)
    sort = forms.ChoiceField(
        required=False,
        choices=[
            ("-logged_at", "Date (newest first)"),
            ("logged_at", "Date (oldest first)"),
            ("employee__name", "Employee (A-Z)"),
            ("item__name", "Item (A-Z)"),
            ("-quantity", "Quantity (high to low)"),
        ],
    )


class StockReportFilterForm(forms.Form):
    date_from = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    date_to = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    item = forms.ModelChoiceField(queryset=Item.objects.all().order_by("name"), required=False)
    sort = forms.ChoiceField(
        required=False,
        choices=[
            ("-updated_at", "Date (newest first)"),
            ("updated_at", "Date (oldest first)"),
            ("item__name", "Item (A-Z)"),
            ("-quantity_added", "Quantity (high to low)"),
        ],
    )


class CSVImportForm(forms.Form):
    csv_file = forms.FileField(label="CSV file")
    update_existing = forms.BooleanField(
        required=False,
        label="Update existing records instead of skipping them",
        help_text="If unchecked, rows matching an existing code/name are left untouched.",
    )


class BulkDeactivateForm(forms.Form):
    csv_file = forms.FileField(label="CSV file (must have a \"code\" column)")
