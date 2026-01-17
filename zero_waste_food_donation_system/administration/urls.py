from django.urls import path
from . import views

urlpatterns = [
    path("", views.admin_login, name="admin_login"),
    path("logout/", views.admin_logout, name="admin_logout"),
    path("dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("donors/", views.donors_list, name="donors_list"),
    path("receivers/", views.receivers_list, name="receivers_list"),
    path("donations/", views.donations_list, name="donations_list"),
    path("pickups/", views.pickups_list, name="pickups_list"),
    path("analytics/", views.analytics_view, name="analytics"),
]
