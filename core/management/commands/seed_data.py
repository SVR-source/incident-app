from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import Store, Profile, Machine, ErrorType


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        # Stores
        store1, _ = Store.objects.get_or_create(store_number='0001', defaults={'address': 'Cầu Giấy, Hà Nội'})
        store2, _ = Store.objects.get_or_create(store_number='0002', defaults={'address': 'Đống Đa, Hà Nội'})
        store3, _ = Store.objects.get_or_create(store_number='0003', defaults={'address': 'Hai Bà Trưng, Hà Nội'})

        # Helper
        def mk(username, role, full_name, phone='0900000000', email='', store=None, rate=30000):
            u, c = User.objects.get_or_create(username=username, defaults={'email': email})
            if c:
                u.set_password('123456')
                u.email = email
                u.save()
            p = u.profile
            p.role = role
            p.full_name = full_name
            p.phone = phone
            p.assigned_store = store
            p.hourly_rate = rate
            p.save()
            return u

        # BOD
        mk('bod1', 'bod', 'Nguyễn Văn BOD', '0901111111', 'bod@company.com')

        # Core team (4 PIC)
        ct_dien = mk('ct_dien', 'core_team', 'KT Điện', '0902222222', 'dien@company.com')
        ct_co   = mk('ct_co', 'core_team', 'KT Cơ', '0902222223', 'co@company.com')
        ct_it   = mk('ct_it', 'core_team', 'IT Support', '0902222224', 'it@company.com')
        ct_vh   = mk('ct_vh', 'core_team', 'Vận hành', '0902222225', 'vh@company.com')

        # Senior (gán cho từng tiệm)
        mk('senior1', 'senior_staff', 'Trưởng tiệm 0001', '0903333331', 'sn1@company.com', store=store1, rate=50000)
        mk('senior2', 'senior_staff', 'Trưởng tiệm 0002', '0903333332', 'sn2@company.com', store=store2, rate=50000)

        # Staff
        mk('nv1', 'staff', 'Nhân viên A', '0904444441', 'nv1@company.com', rate=30000)
        mk('nv2', 'staff', 'Nhân viên B', '0904444442', 'nv2@company.com', rate=30000)
        mk('nv3', 'staff', 'Nhân viên C', '0904444443', 'nv3@company.com', rate=30000)

        # Machines per store
        for store in [store1, store2, store3]:
            for i in range(1, 7):
                Machine.objects.get_or_create(store=store, machine_type='washer', machine_no=i)
            for i in range(1, 5):
                Machine.objects.get_or_create(store=store, machine_type='dryer', machine_no=i)

        # Error types
        errors = [
            ("Máy không khởi động", "⚡", ct_dien, 1),
            ("Máy không xả nước", "💧", ct_co, 2),
            ("Máy không cấp nước", "🚰", ct_co, 3),
            ("Máy sấy không nóng", "🔥", ct_dien, 4),
            ("Lỗi thẻ / thanh toán", "💳", ct_it, 5),
            ("Hết bột giặt / nước xả", "🧴", ct_vh, 6),
            ("Cửa máy không đóng/mở", "🚪", ct_co, 7),
            ("Báo lỗi màn hình", "📺", ct_dien, 8),
            ("Vệ sinh / rò rỉ nước", "🧹", ct_vh, 9),
            ("Khác", "❓", ct_vh, 10),
        ]
        for name, icon, pic, order in errors:
            ErrorType.objects.update_or_create(
                name=name,
                defaults={'icon': icon, 'default_pic': pic, 'order': order, 'active': True}
            )

        self.stdout.write(self.style.SUCCESS("✅ Seed thành công!"))