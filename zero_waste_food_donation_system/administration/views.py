from django.shortcuts import render, redirect
from django.contrib.auth.hashers import check_password
from core.models import Donor, Receiver, FoodDonation, PickupSchedule, MLPredictions
from .models import Admin
from .forms import AdminLoginForm
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import timedelta
import json
from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth


def admin_login(request):
    if request.method == 'POST':
        form = AdminLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            try:
                admin_user = Admin.objects.get(username=username)
                if check_password(password, admin_user.password):
                    request.session['admin_id'] = admin_user.id
                    return redirect('admin_dashboard')
                else:
                    form.add_error(None, "Invalid password")
            except Admin.DoesNotExist:
                form.add_error(None, "Admin not found")
    else:
        form = AdminLoginForm()
    
    return render(request, 'administration/login.html', {
        'form': form,
        'user_type': 'admin'
    })


def admin_dashboard(request):
    if not request.session.get('admin_id'):
        return redirect('admin_login')

    # Basic counts
    donors_count = Donor.objects.count()
    receivers_count = Receiver.objects.count()
    donations_count = FoodDonation.objects.count()
    pickups_count = PickupSchedule.objects.count()

    # Status-based counts
    available_donations = FoodDonation.objects.filter(status='available').count()
    reserved_donations = FoodDonation.objects.filter(status='reserved').count()
    completed_donations = FoodDonation.objects.filter(status='completed').count()

    # Pickup status counts
    pending_pickups = PickupSchedule.objects.filter(pickup_status='pending').count()
    accepted_pickups = PickupSchedule.objects.filter(pickup_status='accepted').count()
    rejected_pickups = PickupSchedule.objects.filter(pickup_status='rejected').count()

    # Recent activity (last 7 days)
    week_ago = timezone.now() - timedelta(days=7)
    recent_donations = FoodDonation.objects.filter(created_at__gte=week_ago).count()
    recent_pickups = PickupSchedule.objects.filter(scheduled_time__gte=week_ago).count()

    # Statistics
    total_quantity = FoodDonation.objects.aggregate(total=Sum('quantity'))['total'] or 0
    avg_priority = PickupSchedule.objects.aggregate(avg=Avg('priority_score'))['avg'] or 0
    success_rate = (accepted_pickups / pickups_count * 100) if pickups_count > 0 else 0

    # Top performers
    top_donors = Donor.objects.annotate(
        num_donations=Count('fooddonation'),
        total_quantity=Sum('fooddonation__quantity')
    ).order_by('-num_donations')[:5]

    top_receivers = Receiver.objects.annotate(
        num_pickups=Count('pickupschedule'),
        success_rate=Count('pickupschedule', filter=Q(pickupschedule__pickup_status='accepted'))
    ).order_by('-num_pickups')[:5]

    # Food type distribution
    food_type_dist = FoodDonation.objects.values('food_type').annotate(
        count=Count('food_type'),
        total_quantity=Sum('quantity')
    ).order_by('-count')

    # Monthly trend data
    # Monthly trend data - FIXED VERSION
    monthly_trend = []
    current = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    for i in range(6):  # Last 6 months
        # Calculate month start and end
        month_offset = 5 - i  # Start from 5 months ago to current month
        month_date = current - timedelta(days=month_offset * 30)
        month_start = month_date.replace(day=1)
        
        if month_start.month == 12:
            month_end = month_start.replace(year=month_start.year + 1, month=1, day=1) - timedelta(seconds=1)
        else:
            month_end = month_start.replace(month=month_start.month + 1, day=1) - timedelta(seconds=1)
        
        # Get donations for this month
        month_donations = FoodDonation.objects.filter(
            created_at__gte=month_start,
            created_at__lte=month_end
        )
        
        # Get pickups for this month
        month_pickups = PickupSchedule.objects.filter(
            scheduled_time__gte=month_start,
            scheduled_time__lte=month_end
        )
        
        monthly_trend.append({
            'month': month_start.strftime('%b %Y'),
            'donations': month_donations.count(),
            'pickups': month_pickups.count(),
            'quantity': month_donations.aggregate(total=Sum('quantity'))['total'] or 0
        })

    # Debug: Print monthly trend data
    print("DEBUG: Monthly trend data:", monthly_trend)

    context = {
        'user_type': 'admin',
        'donors_count': donors_count,
        'receivers_count': receivers_count,
        'donations_count': donations_count,
        'pickups_count': pickups_count,
        'available_donations': available_donations,
        'reserved_donations': reserved_donations,
        'completed_donations': completed_donations,
        'pending_pickups': pending_pickups,
        'accepted_pickups': accepted_pickups,
        'rejected_pickups': rejected_pickups,
        'recent_donations': recent_donations,
        'recent_pickups': recent_pickups,
        'total_quantity': total_quantity,
        'avg_priority': round(avg_priority, 2),
        'success_rate': round(success_rate, 1),
        'top_donors': top_donors,
        'top_receivers': top_receivers,
        'food_type_dist': food_type_dist,
        'monthly_trend': monthly_trend,
        'monthly_trend_json': json.dumps(monthly_trend),  # Add JSON version
    }

    return render(request, 'administration/dashboard.html', context)

def admin_logout(request):
    request.session.flush()
    return redirect("admin_login")

def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if "admin_id" not in request.session:
            return redirect("admin_login")
        return view_func(request, *args, **kwargs)
    return wrapper

# --- Donors ---
@admin_required
def donors_list(request):
    donors = Donor.objects.annotate(
        donation_count=Count('fooddonation'),
        total_quantity=Sum('fooddonation__quantity')
    ).order_by('-donation_count')
    
    return render(request, "administration/donors.html", {
        "donors": donors,
        "user_type": "admin"
    })

# --- Receivers ---
@admin_required
def receivers_list(request):
    receivers = Receiver.objects.annotate(
        pickup_count=Count('pickupschedule'),
        successful_pickups=Count('pickupschedule', filter=Q(pickupschedule__pickup_status='accepted')),
        total_quantity=Sum('pickupschedule__donation_id__quantity', filter=Q(pickupschedule__pickup_status='accepted'))
    ).order_by('-pickup_count')
    
    return render(request, "administration/receivers.html", {
        "receivers": receivers,
        "user_type": "admin"
    })

# --- Donations ---
@admin_required
def donations_list(request):
    donations = FoodDonation.objects.select_related('donor_id', 'assigned_receiver').order_by('-created_at')
    
    return render(request, "administration/donations.html", {
        "donations": donations,
        "user_type": "admin"
    })

# --- Pickups ---
@admin_required
def pickups_list(request):
    pickups = PickupSchedule.objects.select_related('donation_id', 'receiver_id').order_by('-scheduled_time')
    
    return render(request, "administration/pickups.html", {
        "pickups": pickups,
        "user_type": "admin"
    })

# --- Analytics ---
# --- Analytics ---
@admin_required
def analytics_view(request):
    # Food type analytics
    food_type_analytics = list(FoodDonation.objects.values('food_type').annotate(
        count=Count('food_type'),
        total_quantity=Sum('quantity'),
        avg_quantity=Avg('quantity')
    ).order_by('-count'))
    
    # Status distribution
    status_distribution = list(FoodDonation.objects.values('status').annotate(
        count=Count('status')
    ).order_by('-count'))
    
    # Pickup success analytics
    pickup_analytics = list(PickupSchedule.objects.values('pickup_status').annotate(
        count=Count('pickup_status'),
        avg_priority=Avg('priority_score')
    ).order_by('-count'))
    
    # Monthly performance
    monthly_performance = []
    current = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    for i in range(12):  # Last 12 months
        months_ago = 11 - i
        target_date = current - timedelta(days=months_ago * 30)
        target_month = target_date.month
        target_year = target_date.year
        
        month_start = timezone.datetime(target_year, target_month, 1, tzinfo=timezone.get_current_timezone())
        
        if target_month == 12:
            month_end = timezone.datetime(target_year + 1, 1, 1, tzinfo=timezone.get_current_timezone()) - timedelta(seconds=1)
        else:
            month_end = timezone.datetime(target_year, target_month + 1, 1, tzinfo=timezone.get_current_timezone()) - timedelta(seconds=1)
        
        month_donations = FoodDonation.objects.filter(created_at__range=[month_start, month_end])
        month_pickups = PickupSchedule.objects.filter(scheduled_time__range=[month_start, month_end])
        month_accepted_pickups = PickupSchedule.objects.filter(
            scheduled_time__range=[month_start, month_end],
            pickup_status='accepted'
        )
        
        total_pickups = month_pickups.count()
        success_rate = (month_accepted_pickups.count() / total_pickups * 100) if total_pickups > 0 else 0
        
        monthly_performance.append({
            'month': month_start.strftime('%b %Y'),
            'donations': month_donations.count(),
            'pickups': total_pickups,
            'success_rate': round(success_rate, 1)
        })

    context = {
        "food_type_analytics": food_type_analytics,        # ✅ list instead of QuerySet
        "status_distribution": status_distribution,        # ✅ list instead of QuerySet
        "pickup_analytics": pickup_analytics,              # ✅ list instead of QuerySet
        "monthly_performance": monthly_performance,        # already a list
        "user_type": "admin"
    }

    return render(request, "administration/analytics.html", context)
