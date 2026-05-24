from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from collections import defaultdict
from .models import Attendance, ErrorType, Machine, IncidentReport, Profile, Store


def get_role(user):
    return user.profile.role if hasattr(user, 'profile') else 'staff'


def get_effective_role(user, store_id=None, office_mode=False):
    base = get_role(user)
    if base == 'bod':
        return 'bod'
    if base == 'core_team':
        return 'core_team' if office_mode else 'staff'
    if base == 'senior_staff':
        if store_id and user.profile.assigned_store_id == int(store_id):
            return 'senior_staff'
        return 'staff'
    return 'staff'


def login_view(request):
    if request.user.is_authenticated:
        return redirect('select_mode')
    if request.method == 'POST':
        user = authenticate(request,
                            username=request.POST.get('username'),
                            password=request.POST.get('password'))
        if user:
            login(request, user)
            # Check buộc đổi password lần đầu
            if hasattr(user, 'profile') and user.profile.must_change_password:
                messages.warning(request, '⚠️ Vui lòng đổi mật khẩu lần đầu đăng nhập')
                return redirect('change_password')
            return redirect('select_mode')
        messages.error(request, 'Sai tên đăng nhập hoặc mật khẩu')
    return render(request, 'core/login.html')


def logout_view(request):
    for k in ['selected_store_id', 'office_mode', 'effective_role']:
        request.session.pop(k, None)
    logout(request)
    return redirect('login')


@login_required
def select_mode(request):
    role = get_role(request.user)
    stores = Store.objects.all()

    if role == 'bod':
        request.session['effective_role'] = 'bod'
        request.session['office_mode'] = False
        request.session['selected_store_id'] = None
        return redirect('home')

    if request.method == 'POST':
        mode = request.POST.get('mode')
        if mode == 'office' and role == 'core_team':
            request.session['office_mode'] = True
            request.session['selected_store_id'] = None
            request.session['effective_role'] = 'core_team'
        else:
            store_id = request.POST.get('store_id')
            if not store_id:
                messages.error(request, 'Vui lòng chọn tiệm')
                return redirect('select_mode')
            request.session['office_mode'] = False
            request.session['selected_store_id'] = int(store_id)
            request.session['effective_role'] = get_effective_role(request.user, store_id, False)
        return redirect('home')

    return render(request, 'core/select_mode.html', {
        'stores': stores,
        'role': role,
        'can_office': role == 'core_team',
    })


@login_required
def home(request):
    er = request.session.get('effective_role')
    if not er:
        return redirect('select_mode')
    if er == 'bod':
        return bod_dashboard(request)
    if er == 'core_team':
        return core_team_office(request)
    if er == 'senior_staff':
        return senior_home(request)
    return staff_home(request)


def staff_home(request):
    store = get_object_or_404(Store, id=request.session.get('selected_store_id'))
    current = Attendance.objects.filter(user=request.user, check_out__isnull=True).first()
    recent = IncidentReport.objects.filter(reporter=request.user, store=store)[:5]
    return render(request, 'core/home_staff.html', {
        'store': store, 'current_attendance': current, 'recent': recent,
        'is_senior': False,
    })


def senior_home(request):
    store = get_object_or_404(Store, id=request.session.get('selected_store_id'))
    current = Attendance.objects.filter(user=request.user, check_out__isnull=True).first()
    recent = IncidentReport.objects.filter(store=store)[:8]
    return render(request, 'core/home_staff.html', {
        'store': store, 'current_attendance': current, 'recent': recent,
        'is_senior': True,
    })


def core_team_office(request):
    incidents = IncidentReport.objects.filter(
        Q(pic=request.user) | Q(status__in=['new', 'in_progress'])
    ).select_related('store', 'machine', 'error_type', 'reporter').order_by('-created_at')[:80]
    return render(request, 'core/home_core_office.html', {
        'incidents': incidents,
        'me_id': request.user.id,
    })


def bod_dashboard(request):
    stores = Store.objects.all()
    today = timezone.now().date()
    data = []
    for s in stores:
        # Lỗi đang chờ / đang xử lý
        active = IncidentReport.objects.filter(store=s).exclude(status='resolved') \
            .select_related('machine', 'error_type', 'pic', 'handler', 'pic__profile', 'handler__profile') \
            .order_by('-created_at')
        # Lỗi đã hoàn thành hôm nay
        resolved = IncidentReport.objects.filter(
            store=s, status='resolved', resolved_at__date=today
        ).select_related('machine', 'error_type', 'handler', 'handler__profile').order_by('-resolved_at')

        data.append({
            'store': s,
            'active': active,
            'resolved': resolved,
            'resolved_count': resolved.count(),
        })
    return render(request, 'core/home_bod.html', {'store_data': data})


@login_required
def check_in(request):
    er = request.session.get('effective_role')
    if er not in ('staff', 'senior_staff'):
        messages.error(request, 'Bạn không có quyền chấm công')
        return redirect('home')
    store = get_object_or_404(Store, id=request.session.get('selected_store_id'))
    if Attendance.objects.filter(user=request.user, check_out__isnull=True).exists():
        messages.warning(request, 'Bạn đang trong ca làm việc')
    else:
        Attendance.objects.create(user=request.user, store=store, effective_role=er)
        messages.success(request, f'✅ Đã chấm công vào ca tại {store.display_name}')
    return redirect('home')


@login_required
def check_out(request):
    att = Attendance.objects.filter(user=request.user, check_out__isnull=True).first()
    if att:
        att.check_out = timezone.now()
        att.save()
        messages.success(request, f'✅ Kết thúc ca. Tổng: {att.hours_worked} giờ')
    return redirect('home')


@login_required
def report_error(request):
    er = request.session.get('effective_role')
    if er not in ('staff', 'senior_staff'):
        messages.error(request, 'Chỉ nhân viên mới được báo lỗi')
        return redirect('home')
    return render(request, 'core/report_error.html', {
        'errors': ErrorType.objects.filter(active=True),
    })


@login_required
def select_machine(request, error_id):
    error = get_object_or_404(ErrorType, id=error_id)
    store = get_object_or_404(Store, id=request.session.get('selected_store_id'))
    if request.method == 'POST':
        machine = get_object_or_404(Machine, id=request.POST.get('machine_id'))
        IncidentReport.objects.create(
            reporter=request.user, store=store, machine=machine,
            error_type=error, pic=error.default_pic,
            note=request.POST.get('note', ''),
        )
        messages.success(request, '✅ Báo cáo sự cố đã gửi')
        return redirect('home')
    return render(request, 'core/select_machine.html', {
        'error': error, 'machines': Machine.objects.filter(store=store),
    })


@login_required
def my_hours(request):
    month = int(request.GET.get('month', timezone.now().month))
    year = int(request.GET.get('year', timezone.now().year))
    atts = Attendance.objects.filter(
        user=request.user, check_in__year=year, check_in__month=month, check_out__isnull=False
    ).order_by('check_in')
    total = sum(a.hours_worked for a in atts)
    rate = float(request.user.profile.hourly_rate) if hasattr(request.user, 'profile') else 0
    return render(request, 'core/my_hours.html', {
        'attendances': atts, 'total_hours': round(total, 2),
        'total_salary': total * rate, 'month': month, 'year': year, 'rate': rate,
    })


@login_required
def store_hours(request):
    if request.session.get('effective_role') != 'senior_staff':
        messages.error(request, 'Chỉ Senior Staff mới xem được')
        return redirect('home')
    store = get_object_or_404(Store, id=request.session.get('selected_store_id'))
    month = int(request.GET.get('month', timezone.now().month))
    year = int(request.GET.get('year', timezone.now().year))
    atts = Attendance.objects.filter(
        store=store, check_in__year=year, check_in__month=month, check_out__isnull=False
    ).select_related('user', 'user__profile').order_by('user__username')

    data = defaultdict(lambda: {'attendances': [], 'total_hours': 0, 'salary': 0})
    for a in atts:
        d = data[a.user.id]
        d['user'] = a.user
        d['attendances'].append(a)
        d['total_hours'] += a.hours_worked
    for uid, d in data.items():
        rate = float(d['user'].profile.hourly_rate) if hasattr(d['user'], 'profile') else 0
        d['rate'] = rate
        d['salary'] = d['total_hours'] * rate
        d['total_hours'] = round(d['total_hours'], 2)

    return render(request, 'core/store_hours.html', {
        'store': store, 'user_data': dict(data), 'month': month, 'year': year,
    })


@login_required
def incident_action(request, incident_id, action):
    if request.session.get('effective_role') != 'core_team':
        messages.error(request, 'Không có quyền')
        return redirect('home')
    inc = get_object_or_404(IncidentReport, id=incident_id)
    if inc.pic_id != request.user.id:
        messages.error(request, 'Lỗi này không gán cho bạn')
        return redirect('home')
    if action == 'in_progress' and inc.status == 'new':
        inc.status = 'in_progress'
        inc.in_progress_at = timezone.now()
        inc.handler = request.user
        inc.save()
        messages.success(request, '⏱ Bắt đầu xử lý')
    elif action == 'resolved' and inc.status == 'in_progress':
        inc.status = 'resolved'
        inc.resolved_at = timezone.now()
        inc.save()
        messages.success(request, '✅ Hoàn thành')
    return redirect('home')

from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.urls import reverse


@login_required
def change_password(request):
    if request.method == 'POST':
        old = request.POST.get('old_password')
        new1 = request.POST.get('new_password1')
        new2 = request.POST.get('new_password2')

        if not request.user.check_password(old):
            messages.error(request, 'Mật khẩu cũ không đúng')
        elif new1 != new2:
            messages.error(request, 'Mật khẩu mới không khớp')
        elif len(new1) < 6:
            messages.error(request, 'Mật khẩu mới phải ít nhất 6 ký tự')
        elif new1 == '123456':
            messages.error(request, 'Không được dùng mật khẩu mặc định 123456')
        else:
            request.user.set_password(new1)
            request.user.save()
            if hasattr(request.user, 'profile'):
                request.user.profile.must_change_password = False
                request.user.profile.save()
            update_session_auth_hash(request, request.user)
            messages.success(request, '✅ Đổi mật khẩu thành công!')
            return redirect('select_mode')

    return render(request, 'core/change_password.html', {
        'force': request.user.profile.must_change_password if hasattr(request.user, 'profile') else False
    })


def forgot_password(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        users = User.objects.filter(email__iexact=email)
        if users.exists():
            user = users.first()
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_url = request.build_absolute_uri(
                reverse('reset_password', args=[uid, token])
            )
            send_mail(
                subject='[Incident Manager] Reset mật khẩu',
                message=f'''Xin chào {user.profile.full_name or user.username},

Bạn (hoặc ai đó) đã yêu cầu reset mật khẩu cho tài khoản này.
Click vào link dưới đây để đặt lại mật khẩu (link có hiệu lực trong 1 giờ):

{reset_url}

Nếu không phải bạn, vui lòng bỏ qua email này.

Trân trọng,
Incident Manager''',
                from_email=None,
                recipient_list=[email],
                fail_silently=False,
            )
        # Luôn báo success để tránh leak email tồn tại hay không
        messages.success(request, '✅ Nếu email tồn tại, link reset đã được gửi. Vui lòng kiểm tra hộp thư.')
        return redirect('login')
    return render(request, 'core/forgot_password.html')


def reset_password(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, User.DoesNotExist):
        user = None

    if user is None or not default_token_generator.check_token(user, token):
        messages.error(request, '❌ Link reset không hợp lệ hoặc đã hết hạn')
        return redirect('forgot_password')

    if request.method == 'POST':
        new1 = request.POST.get('new_password1')
        new2 = request.POST.get('new_password2')
        if new1 != new2:
            messages.error(request, 'Mật khẩu không khớp')
        elif len(new1) < 6:
            messages.error(request, 'Mật khẩu phải ít nhất 6 ký tự')
        else:
            user.set_password(new1)
            user.save()
            if hasattr(user, 'profile'):
                user.profile.must_change_password = False
                user.profile.save()
            messages.success(request, '✅ Đặt lại mật khẩu thành công! Vui lòng đăng nhập.')
            return redirect('login')

    return render(request, 'core/reset_password.html', {'user_obj': user})

from django.http import JsonResponse, HttpResponse


def manifest(request):
    return JsonResponse({
        "name": "Incident Manager",
        "short_name": "Incident",
        "description": "Quản lý báo cáo sự cố cửa hàng",
        "start_url": "/",
        "display": "standalone",
        "orientation": "portrait",
        "background_color": "#1F4E78",
        "theme_color": "#1F4E78",
        "icons": [
            {
                "src": "https://api.iconify.design/twemoji/basket.svg?width=192",
                "sizes": "192x192",
                "type": "image/svg+xml"
            },
            {
                "src": "https://api.iconify.design/twemoji/basket.svg?width=512",
                "sizes": "512x512",
                "type": "image/svg+xml"
            }
        ]
    })


def service_worker(request):
    sw = '''
const CACHE = 'incident-v1';
self.addEventListener('install', e => {
    self.skipWaiting();
});
self.addEventListener('activate', e => {
    e.waitUntil(clients.claim());
});
self.addEventListener('fetch', e => {
    if (e.request.method !== 'GET') return;
    e.respondWith(
        fetch(e.request).catch(() => caches.match(e.request))
    );
});
'''
    return HttpResponse(sw, content_type='application/javascript')