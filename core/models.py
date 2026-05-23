from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

ROLE_CHOICES = [
    ('bod', 'BOD'),
    ('core_team', 'Core Team'),
    ('senior_staff', 'Senior Staff'),
    ('staff', 'Staff'),
]

STATUS_CHOICES = [
    ('new', 'Mới'),
    ('in_progress', 'Đang xử lý'),
    ('resolved', 'Hoàn thành'),
]

MACHINE_TYPE = [
    ('washer', 'Máy giặt'),
    ('dryer', 'Máy sấy'),
]


class Store(models.Model):
    store_number = models.CharField(max_length=10, unique=True, help_text="Ví dụ: 0001, 0002")
    address = models.CharField(max_length=255)

    class Meta:
        ordering = ['store_number']

    @property
    def display_name(self):
        return f"DT{self.store_number} - {self.address}"

    def __str__(self):
        return self.display_name


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=15, choices=ROLE_CHOICES, default='staff')
    full_name = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    assigned_store = models.ForeignKey(
        Store, on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Tiệm được gán (chỉ dùng cho Senior Staff)"
    )
    hourly_rate = models.DecimalField(
        max_digits=10, decimal_places=0, default=30000,
        help_text="Lương theo giờ (VND)"
    )
    must_change_password = models.BooleanField(
        default=True,
        help_text="Bắt buộc đổi mật khẩu lần đăng nhập đầu"
    )

    def __str__(self):
        return f"{self.full_name or self.user.username} ({self.get_role_display()})"

class Machine(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='machines')
    machine_type = models.CharField(max_length=10, choices=MACHINE_TYPE)
    machine_no = models.IntegerField()

    class Meta:
        unique_together = ('store', 'machine_type', 'machine_no')
        ordering = ['machine_type', 'machine_no']

    def __str__(self):
        return f"{self.get_machine_type_display()} #{self.machine_no}"


class ErrorType(models.Model):
    name = models.CharField(max_length=200)
    default_pic = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='handled_errors',
        help_text="Người Core Team xử lý lỗi này"
    )
    icon = models.CharField(max_length=10, default='⚠️')
    active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.name


class Attendance(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    effective_role = models.CharField(max_length=15, choices=ROLE_CHOICES, default='staff')
    check_in = models.DateTimeField(auto_now_add=True)
    check_out = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-check_in']

    @property
    def hours_worked(self):
        if self.check_out:
            return round((self.check_out - self.check_in).total_seconds() / 3600, 2)
        return 0


class IncidentReport(models.Model):
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports')
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE)
    error_type = models.ForeignKey(ErrorType, on_delete=models.CASCADE)
    pic = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='assigned_incidents'
    )
    handler = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='handling_incidents'
    )
    note = models.TextField(blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='new')
    created_at = models.DateTimeField(auto_now_add=True)
    in_progress_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    @property
    def processing_seconds(self):
        if not self.in_progress_at:
            return 0
        end = self.resolved_at or timezone.now()
        return int((end - self.in_progress_at).total_seconds())

    @property
    def processing_duration(self):
        s = self.processing_seconds
        if s == 0:
            return "-"
        h, rem = divmod(s, 3600)
        m, sec = divmod(rem, 60)
        if h > 0:
            return f"{h}h {m}m {sec}s"
        if m > 0:
            return f"{m}m {sec}s"
        return f"{sec}s"

    @property
    def waiting_duration(self):
        if self.status == 'new':
            mins = int((timezone.now() - self.created_at).total_seconds() / 60)
            return f"{mins // 60}h {mins % 60}m"
        return None