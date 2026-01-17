from django.urls import path
from . import views

app_name = 'donors'

urlpatterns = [
    path('', views.donor_login, name='donor_login'),
    path('register/', views.donor_registration, name='donor_registration'),  # Verify this line
    path('dashboard/', views.donor_dashboard, name='dashboard'),
    path('donation-entry/', views.donation_entry, name='donation_entry'),
    path('profile/', views.profile, name='profile'),
    path('check_requests/<int:donor_id>/', views.check_requests, name='check_requests'),
    path('add_address/', views.add_address, name='add_address'),
        # Analytics URLs
    path('analytics/', views.donor_analytics, name='analytics'),
    path('analytics/data/', views.donor_analytics_data, name='analytics_data'),

]