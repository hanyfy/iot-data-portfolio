"""
URL configuration for alpes_echo project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from webhook import views
from django.contrib.auth import views as auth_views


urlpatterns = [
    path("admin/", admin.site.urls),
    path('webhook/', views.webhook, name='webhook'),
    path('sv_webhook/', views.sv_webhook, name='sv_webhook'),
    path('sv_geofencing/', views.sv_geofencing, name='sv_geofencing'),
    path('sv_telemetry/', views.sv_telemetry, name='sv_telemetry'),
    path('sv_analysis/', views.sv_analysis, name='sv_analysis'),
    path('upd_geofencing/<int:id>', views.upd_geofencing, name='upd_geofencing'),
    path('upd_webhook/<int:id>', views.upd_webhook, name='upd_webhook'),
    path('upd_analysis/<int:id>', views.upd_analysis, name='upd_analysis'),
    path('upd_telemetry/<int:id>', views.upd_telemetry, name='upd_telemetry'),
    path('del_geofencing/<int:id>', views.del_geofencing, name='del_geofencing'),
    path('del_webhook/<int:id>', views.del_webhook, name='del_webhook'),
    path('del_telemetry/<int:id>', views.del_telemetry, name='del_telemetry'),
    path('del_analysis/<int:id>', views.del_analysis, name='del_analysis'),
    path('',views.login_view, name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout')
]
