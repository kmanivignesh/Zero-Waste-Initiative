from django.shortcuts import render, redirect
from .forms import DonorRegistrationForm, DonationEntryForm
from core.models import Donor, FoodDonation, PickupSchedule, Receiver
from django.contrib.auth.hashers import check_password,make_password
from django.http import HttpResponseRedirect
import logging
from django.http import JsonResponse
from django.contrib import messages

from django.shortcuts import render, redirect
from django.contrib.auth.hashers import make_password, check_password
from .forms import DonorRegistrationForm, DonationEntryForm, ProfileUpdateForm
from core.models import Donor, DonorAddress, FoodDonation, PickupSchedule
import logging
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import datetime, timedelta
import json
from collections import defaultdict

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def donor_registration(request):
    if request.method == 'POST':
        form = DonorRegistrationForm(request.POST)
        if form.is_valid():
            donor = form.save()
            logger.debug("Donor registered: %s", donor.donor_id)
            
            # Show success message and redirect to login page
            messages.success(request, 'Registration successful! Please login with your credentials.')
            return redirect('main:auth')  # Redirect to main login page
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = DonorRegistrationForm()
    
    return render(request, 'donors/registration.html', {
        'form': form,
        'user_type': 'donor'
    })

# ... (rest of the views remain unchanged)
def donor_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        try:
            donor = Donor.objects.get(name=username)
            if check_password(password, donor.password):
                request.session['donor_id'] = donor.donor_id
                return redirect('donors:dashboard')
        except Donor.DoesNotExist:
            pass
    return render(request, 'auth.html', {'action': 'login', 'user_type': 'donor'})

def donor_dashboard(request):
    if 'donor_id' not in request.session:
        return redirect('donors:donor_login')
    donor = Donor.objects.get(donor_id=request.session['donor_id'])

    donations = FoodDonation.objects.filter(donor_id=donor)
    pending_pickups = PickupSchedule.objects.filter(donation_id__donor_id=donor, pickup_status='pending')
    accepted_pickups = PickupSchedule.objects.filter(donation_id__donor_id=donor, pickup_status='accepted')

    if request.method == 'POST':
        schedule_id = request.POST.get('schedule_id')
        action = request.POST.get('action')
        if schedule_id:
            pickup = PickupSchedule.objects.get(schedule_id=schedule_id)
            if action == 'accept':
                # Accept this receiver
                pickup.pickup_status = 'accepted'
                pickup.save()

                # Mark donation as reserved and store receiver
                donation = pickup.donation_id
                donation.status = 'reserved'
                donation.assigned_receiver = pickup.receiver_id
                donation.save()

                # Reject other pending pickups for this donation
                other_pickups = PickupSchedule.objects.filter(
                    donation_id=donation, pickup_status='pending'
                ).exclude(schedule_id=schedule_id)
                for op in other_pickups:
                    op.pickup_status = 'rejected'
                    op.save()
                    # Here you can send notification to receivers (WebSocket/Email)
                
            elif action == 'reject':
                pickup.pickup_status = 'rejected'
                pickup.save()
        return redirect('donors:dashboard')

    return render(request, 'dashboard.html', {
        'user_type': 'donor',
        'donations': donations,
        'pending_pickups': pending_pickups,
        'accepted_pickups' : accepted_pickups,
        'donor_name' : donor.name,
        
    })

def donation_entry(request):
    if 'donor_id' not in request.session:
        return redirect('donors:donor_login')
    if request.method == 'POST':
        form = DonationEntryForm(request.POST)
        if form.is_valid():
            donation = form.save(commit=False)
            donation.donor_id = Donor.objects.get(donor_id=request.session['donor_id'])
            donation.save()
            logger.debug("Donation saved: ID=%s, Donor=%s", donation.donation_id, donation.donor_id.donor_id)
            return redirect('donors:dashboard')
    else:
        form = DonationEntryForm()
    return render(request, 'donors/donation_entry.html', {'form': form})

def profile(request):
    if 'donor_id' not in request.session:
        return redirect('donors:donor_login')
    donor_id = request.session['donor_id']
    donor = Donor.objects.get(donor_id=donor_id)
    addresses = DonorAddress.objects.filter(donor_id=donor_id)
    if request.method == 'POST':
        if 'new_address' in request.POST:
            address = request.POST.get('new_address')
            DonorAddress.objects.create(donor_id=donor, address=address)
            return redirect('donors:profile')
        form = ProfileUpdateForm(request.POST, instance=donor)
        if form.is_valid():
            form.save()
            return redirect('donors:profile')
    else:
        form = ProfileUpdateForm(instance=donor)
    return render(request, 'profile.html', {'user': donor, 'addresses': addresses, 'form': form})

def check_requests(request, donor_id):
    pickups = PickupSchedule.objects.filter(donation_id__donor_id=donor_id, pickup_status='pending')
    if pickups.exists():
        return JsonResponse({'message': 'New pickup request available.'})
    return JsonResponse({'message': ''})

def notify_receiver(receiver_id, schedule_id, status):
    pass  # Placeholder for WebSocket or real-time notification

def add_address(request):
    if 'donor_id' not in request.session:
        return redirect('donors:donor_login')
    if request.method == 'POST':
        address = request.POST.get('new_address')
        donor = Donor.objects.get(donor_id=request.session['donor_id'])
        DonorAddress.objects.create(donor_id=donor, address=address)
        return redirect('donors:profile')
    return redirect('donors:profile')

def donor_analytics(request):
    if 'donor_id' not in request.session:
        return redirect('donors:donor_login')
    
    donor = Donor.objects.get(donor_id=request.session['donor_id'])
    
    # Time period filter
    period = request.GET.get('period', 'month')  # week, month, year, all
    
    # Calculate date range
    end_date = timezone.now()
    if period == 'week':
        start_date = end_date - timedelta(days=7)
    elif period == 'month':
        start_date = end_date - timedelta(days=30)
    elif period == 'year':
        start_date = end_date - timedelta(days=365)
    else:  # all time
        start_date = donor.created_at
    
    # Get donations data
    donations = FoodDonation.objects.filter(
        donor_id=donor,
        created_at__range=[start_date, end_date]
    )
    
    # Basic statistics
    total_donations = donations.count()
    total_quantity = donations.aggregate(total=Sum('quantity'))['total'] or 0
    
    # Status distribution
    status_counts = donations.values('status').annotate(count=Count('status'))
    
    # Food type distribution
    food_type_dist = donations.values('food_type').annotate(
        count=Count('food_type'),
        total_quantity=Sum('quantity')
    )
    
    # Monthly trend data
    monthly_data = []
    current = start_date
    while current <= end_date:
        month_start = current.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if period == 'year':
            next_month = month_start + timedelta(days=32)
            month_end = next_month.replace(day=1) - timedelta(days=1)
        else:
            month_end = month_start + timedelta(days=30)
        
        month_donations = donations.filter(
            created_at__range=[month_start, month_end]
        )
        monthly_data.append({
            'month': month_start.strftime('%b %Y'),
            'count': month_donations.count(),
            'quantity': month_donations.aggregate(total=Sum('quantity'))['total'] or 0
        })
        
        if period == 'year':
            current = next_month
        else:
            break  # For shorter periods, show single month
    
    # Pickup statistics
    pickups = PickupSchedule.objects.filter(donation_id__donor_id=donor)
    pickup_status_dist = pickups.values('pickup_status').annotate(count=Count('pickup_status'))
    
    # Success rate
    successful_pickups = pickups.filter(pickup_status='accepted').count()
    total_pickup_requests = pickups.count()
    success_rate = (successful_pickups / total_pickup_requests * 100) if total_pickup_requests > 0 else 0
    
    # Recent activity
    recent_donations = donations.order_by('-created_at')[:5]
    
    context = {
        'user_type': 'donor',
        'period': period,
        'total_donations': total_donations,
        'total_quantity': total_quantity,
        'success_rate': round(success_rate, 1),
        'status_counts': list(status_counts),
        'food_type_dist': list(food_type_dist),
        'monthly_data': monthly_data,
        'pickup_status_dist': list(pickup_status_dist),
        'recent_donations': recent_donations,
        'start_date': start_date.date(),
        'end_date': end_date.date(),
    }
    
    return render(request, 'analytics/donor_analytics.html', context)

def donor_analytics_data(request):
    """API endpoint for chart data"""
    if 'donor_id' not in request.session:
        return JsonResponse({'error': 'Not authenticated'})
    
    donor = Donor.objects.get(donor_id=request.session['donor_id'])
    period = request.GET.get('period', 'month')
    
    end_date = timezone.now()
    if period == 'week':
        start_date = end_date - timedelta(days=7)
    elif period == 'month':
        start_date = end_date - timedelta(days=30)
    elif period == 'year':
        start_date = end_date - timedelta(days=365)
    else:
        start_date = donor.created_at
    
    # Get donations with proper date filtering
    donations = FoodDonation.objects.filter(
        donor_id=donor,
        created_at__gte=start_date,
        created_at__lte=end_date
    )
    
    print(f"DEBUG: Found {donations.count()} donations between {start_date} and {end_date}")
    
    # Food type distribution for chart
    food_types = list(donations.values('food_type').annotate(
        count=Count('food_type'),
        quantity=Sum('quantity')
    ))
    
    # Status distribution for chart
    status_data = list(donations.values('status').annotate(count=Count('status')))
    
    # Monthly trend for chart - IMPROVED VERSION
    monthly_trend = []
    
    if period == 'year':
        # Generate data for each month of the year
        for i in range(12):
            # Calculate month start and end
            month_date = end_date.replace(day=1)  # Start from current month
            target_month = month_date.month - i
            target_year = month_date.year
            
            if target_month <= 0:
                target_month += 12
                target_year -= 1
            
            month_start = timezone.datetime(target_year, target_month, 1, tzinfo=timezone.get_current_timezone())
            if target_month == 12:
                month_end = timezone.datetime(target_year + 1, 1, 1, tzinfo=timezone.get_current_timezone()) - timedelta(seconds=1)
            else:
                month_end = timezone.datetime(target_year, target_month + 1, 1, tzinfo=timezone.get_current_timezone()) - timedelta(seconds=1)
            
            # Filter donations for this month
            month_donations = donations.filter(
                created_at__gte=month_start,
                created_at__lte=month_end
            )
            
            monthly_trend.append({
                'month': month_start.strftime('%b'),
                'count': month_donations.count(),
                'quantity': month_donations.aggregate(total=Sum('quantity'))['total'] or 0
            })
        
        monthly_trend.reverse()  # Reverse to show chronological order
    
    elif period == 'month':
        # Generate data for last 30 days (weekly chunks)
        for i in range(4):  # 4 weeks
            week_end = end_date - timedelta(days=i * 7)
            week_start = week_end - timedelta(days=6)
            
            week_donations = donations.filter(
                created_at__gte=week_start,
                created_at__lte=week_end
            )
            
            monthly_trend.append({
                'month': week_start.strftime('%m/%d'),
                'count': week_donations.count(),
                'quantity': week_donations.aggregate(total=Sum('quantity'))['total'] or 0
            })
        
        monthly_trend.reverse()
    
    elif period == 'week':
        # Generate data for last 7 days
        for i in range(7):
            day = end_date - timedelta(days=6 - i)  # Start from oldest to newest
            day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            day_donations = donations.filter(
                created_at__gte=day_start,
                created_at__lte=day_end
            )
            
            monthly_trend.append({
                'month': day_start.strftime('%a'),
                'count': day_donations.count(),
                'quantity': day_donations.aggregate(total=Sum('quantity'))['total'] or 0
            })
    
    else:  # all time
        # Group by month for all time
        all_donations = FoodDonation.objects.filter(donor_id=donor)
        dates = all_donations.dates('created_at', 'month')
        
        for date in dates:
            month_start = date.replace(day=1)
            if date.month == 12:
                month_end = date.replace(year=date.year + 1, month=1, day=1) - timedelta(seconds=1)
            else:
                month_end = date.replace(month=date.month + 1, day=1) - timedelta(seconds=1)
            
            month_donations = all_donations.filter(
                created_at__gte=month_start,
                created_at__lte=month_end
            )
            
            monthly_trend.append({
                'month': month_start.strftime('%b %Y'),
                'count': month_donations.count(),
                'quantity': month_donations.aggregate(total=Sum('quantity'))['total'] or 0
            })
    
    # If still no data, use sample data for demonstration
    if not monthly_trend and donations.exists():
        # Only use sample data if there are actual donations but no trend data
        monthly_trend = [
            {'month': 'Jan', 'count': 5, 'quantity': 25},
            {'month': 'Feb', 'count': 8, 'quantity': 40},
            {'month': 'Mar', 'count': 12, 'quantity': 60},
        ]
    
    response_data = {
        'food_types': food_types,
        'status_data': status_data,
        'monthly_trend': monthly_trend,
    }
    
    print(f"DEBUG: Sending response - Food types: {len(food_types)}, Status: {len(status_data)}, Trend: {len(monthly_trend)}")
    
    return JsonResponse(response_data)