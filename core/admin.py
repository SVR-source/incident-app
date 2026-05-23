from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Store, Profile, Machine, ErrorType, Attendance, IncidentReport


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    fields = ('role', 'full_name', 'phone', 'assigned_store', 'hourly_rate')


class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)
    list_display = ('username', 'email', '_fullname', '_phone', '_role', '_store')

    def get_inline_instances(self, request, obj=None):
        # Không hiển thị inline Profile khi đang TẠO user mới (tránh duplicate)
        if obj is None:
            return []
        return super().get_inline_instances(request, obj)

    def _fullname(self, obj):
        return getattr(obj.profile, 'full_name', '') if hasattr(obj, 'profile') else ''
    _fullname.short_description = 'Họ tên'

    def _phone(self, obj):
        return getattr(obj.profile, 'phone', '') if hasattr(obj, 'profile') else ''
    _phone.short_description = 'SĐT'

    def _role(self, obj):
        return obj.profile.get_role_display() if hasattr(obj, 'profile') else ''
    _role.short_description = 'Vai trò'

    def _store(self, obj):
        return obj.profile.assigned_store if hasattr(obj, 'profile') else ''
    _store.short_description = 'Tiệm gán'

admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ('store_number', 'address', 'display_name')
    search_fields = ('store_number', 'address')
    ordering = ('store_number',)


@admin.register(Machine)
class MachineAdmin(admin.ModelAdmin):
    list_display = ('store', 'machine_type', 'machine_no')
    list_filter = ('store', 'machine_type')


@admin.register(ErrorType)
class ErrorTypeAdmin(admin.ModelAdmin):
    list_display = ('order', 'icon', 'name', 'default_pic', 'active')
    list_editable = ('icon', 'name', 'default_pic', 'active', 'order')
    list_display_links = None


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('user', 'store', 'effective_role', 'check_in', 'check_out', 'hours_worked')
    list_filter = ('store', 'effective_role')
    date_hierarchy = 'check_in'


@admin.register(IncidentReport)
class IncidentReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_at', 'store', 'machine', 'error_type', 'pic', 'status', 'in_progress_at', 'resolved_at')
    list_filter = ('status', 'store', 'error_type')
    date_hierarchy = 'created_at'