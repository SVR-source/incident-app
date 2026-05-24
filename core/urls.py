from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('change-password/', views.change_password, name='change_password'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('reset-password/<uidb64>/<token>/', views.reset_password, name='reset_password'),
    path('select-mode/', views.select_mode, name='select_mode'),
    path('', views.home, name='home'),
    path('checkin/', views.check_in, name='check_in'),
    path('checkout/', views.check_out, name='check_out'),
    path('report/', views.report_error, name='report_error'),
    path('report/<int:error_id>/machine/', views.select_machine, name='select_machine'),
    path('my-hours/', views.my_hours, name='my_hours'),
    path('store-hours/', views.store_hours, name='store_hours'),
    path('incident/<int:incident_id>/<str:action>/', views.incident_action, name='incident_action'),
    path('manifest.json', views.manifest, name='manifest'),
    path('sw.js', views.service_worker, name='sw'),
]