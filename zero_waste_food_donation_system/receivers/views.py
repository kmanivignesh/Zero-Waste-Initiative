from django.contrib import messages
from .forms import ReceiverRegistrationForm, ProfileUpdateForm , CapacityUpdateForm
from core.models import Receiver, FoodDonation, PickupSchedule, ReceiverAddress
from django.http import JsonResponse
from ML_Model.ml_model import priority_model, food_type_encoder, scaler
import pandas as pd
from django.shortcuts import render, redirect
from django.contrib.auth.hashers import make_password, check_password
from core.models import Receiver, FoodDonation, PickupSchedule, ReceiverAddress
import logging
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import datetime, timedelta
import json


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def receiver_registration(request):
    if request.method == 'POST':
        form = ReceiverRegistrationForm(request.POST)
        if form.is_valid():
            receiver = form.save()
            logger.debug("Receiver registered: %s", receiver.receiver_id)
            
            # Redirect to login page
            messages.success(request, 'Registration successful! Please login with your credentials.')
            return redirect('main:auth')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ReceiverRegistrationForm()
    
    return render(request, 'receivers/registration.html', {
        'form': form,
        'user_type': 'receiver'
    })

def receiver_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        try:
            receiver = Receiver.objects.get(name=username)
            if check_password(password, receiver.password):
                request.session['receiver_id'] = receiver.receiver_id
                return redirect('receivers:dashboard')
        except Receiver.DoesNotExist:
            pass
    return render(request, 'auth.html', {'action': 'login', 'user_type': 'receiver'})

def receiver_dashboard(request):
    if 'receiver_id' not in request.session:
        return redirect('receivers:receiver_login')
    
    receiver = Receiver.objects.get(receiver_id=request.session['receiver_id'])
    available_donations = FoodDonation.objects.filter(status='available')
    
    # Update priority for each donation for this receiver
    for donation in available_donations:
        donation.calculate_priority_ml(
            receiver_capacity=receiver.capacity,
            receiver_lat=receiver.location_lat,
            receiver_long=receiver.location_long
        )

    accepted_pickups = PickupSchedule.objects.filter(receiver_id=receiver)

    # Handle capacity update
    if request.method == 'POST' and 'update_capacity' in request.POST:
        form = CapacityUpdateForm(request.POST, instance=receiver)
        if form.is_valid():
            form.save()
            messages.success(request, "Capacity updated successfully!")
            return redirect('receivers:dashboard')
    else:
        form = CapacityUpdateForm(instance=receiver)

    return render(request, 'dashboard.html', {
        'user_type': 'receiver',
        'available_donations': available_donations,
        'accepted_pickups': accepted_pickups,
        'capacity_form': form,  # Pass form to template
        'current_capacity':receiver.capacity,
        'receiver_name':receiver.name,
    })



def profile(request):
    if 'receiver_id' not in request.session:
        return redirect('receivers:receiver_login')
    receiver_id = request.session['receiver_id']
    receiver = Receiver.objects.get(receiver_id=receiver_id)
    addresses = ReceiverAddress.objects.filter(receiver_id=receiver_id)
    if request.method == 'POST':
        if 'new_address' in request.POST:
            address = request.POST.get('new_address')
            ReceiverAddress.objects.create(receiver_id=receiver, address=address)
            return redirect('receivers:profile')
        form = ProfileUpdateForm(request.POST, instance=receiver)
        if form.is_valid():
            form.save()
            return redirect('receivers:profile')
    else:
        form = ProfileUpdateForm(instance=receiver)
    return render(request, 'profile.html', {'user': receiver, 'addresses': addresses, 'form': form})

def check_notification(request, receiver_id):
    pickups = PickupSchedule.objects.filter(receiver_id__receiver_id=receiver_id)
    for pickup in pickups:
        if pickup.pickup_status == 'accepted':
            return JsonResponse({'message': f'Pickup {pickup.schedule_id} successfully allocated.'})
        elif pickup.pickup_status == 'rejected':
            return JsonResponse({'message': f'Pickup {pickup.schedule_id} allocated to another receiver.'})
    return JsonResponse({'message': ''})

def schedule_pickup(request, donation_id):
    if 'receiver_id' not in request.session:
        return redirect('receivers:receiver_login')
    if request.method == 'POST':
        receiver = Receiver.objects.get(receiver_id=request.session['receiver_id'])
        donation = FoodDonation.objects.get(donation_id=donation_id)

        # ML-based priority
        priority = donation.calculate_priority_ml(
            receiver_capacity=receiver.capacity,
            receiver_lat=receiver.location_lat,
            receiver_long=receiver.location_long
        )

        PickupSchedule.objects.create(
            donation_id=donation,
            receiver_id=receiver,
            priority_score=priority,
            scheduled_time=donation.expiry_time,
            pickup_status='pending'
        )
        logger.debug("Pickup scheduled for donation %s by receiver %s", donation_id, receiver.receiver_id)
        return redirect('receivers:dashboard')
    return redirect('receivers:dashboard')

def receiver_analytics(request):
    if 'receiver_id' not in request.session:
        return redirect('receivers:receiver_login')
    
    receiver = Receiver.objects.get(receiver_id=request.session['receiver_id'])
    
    # Time period filter
    period = request.GET.get('period', 'month')
    
    # Calculate date range
    end_date = timezone.now()
    if period == 'week':
        start_date = end_date - timedelta(days=7)
    elif period == 'month':
        start_date = end_date - timedelta(days=30)
    elif period == 'year':
        start_date = end_date - timedelta(days=365)
    else:
        start_date = receiver.created_at
    
    # Get pickups data
    pickups = PickupSchedule.objects.filter(
        receiver_id=receiver,
        scheduled_time__range=[start_date, end_date]
    )
    
    # Basic statistics
    total_pickups = pickups.count()
    successful_pickups = pickups.filter(pickup_status='accepted').count()
    success_rate = (successful_pickups / total_pickups * 100) if total_pickups > 0 else 0
    
    # Total quantity received
    total_quantity = 0
    for pickup in pickups.filter(pickup_status='accepted'):
        total_quantity += pickup.donation_id.quantity
    
    # Average priority score
    avg_priority = pickups.aggregate(avg=Avg('priority_score'))['avg'] or 0
    
    # Food type distribution
    food_type_dist = []
    for pickup in pickups.filter(pickup_status='accepted'):
        food_type_dist.append({
            'food_type': pickup.donation_id.food_type,
            'quantity': pickup.donation_id.quantity
        })
    
    # Status distribution
    status_dist = pickups.values('pickup_status').annotate(count=Count('pickup_status'))
    
    # Monthly trend
    monthly_data = []
    current = start_date
    while current <= end_date:
        month_start = current.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if period == 'year':
            next_month = month_start + timedelta(days=32)
            month_end = next_month.replace(day=1) - timedelta(days=1)
        else:
            month_end = month_start + timedelta(days=30)
        
        month_pickups = pickups.filter(scheduled_time__range=[month_start, month_end])
        monthly_data.append({
            'month': month_start.strftime('%b %Y'),
            'count': month_pickups.count(),
            'successful': month_pickups.filter(pickup_status='accepted').count()
        })
        
        if period == 'year':
            current = next_month
        else:
            break
    
    # Recent activity
    recent_pickups = pickups.order_by('-scheduled_time')[:5]
    
    # Capacity utilization
    capacity_utilization = min((total_quantity / receiver.capacity * 100) if receiver.capacity > 0 else 0, 100)
    
    context = {
        'user_type': 'receiver',
        'period': period,
        'total_pickups': total_pickups,
        'successful_pickups': successful_pickups,
        'success_rate': round(success_rate, 1),
        'total_quantity': total_quantity,
        'avg_priority': round(avg_priority, 2),
        'food_type_dist': food_type_dist,
        'status_dist': list(status_dist),
        'monthly_data': monthly_data,
        'recent_pickups': recent_pickups,
        'capacity_utilization': round(capacity_utilization, 1),
        'receiver_capacity': receiver.capacity,
    }
    
    return render(request, 'analytics/receiver_analytics.html', context)

def receiver_analytics_data(request):
    """API endpoint for receiver chart data"""
    if 'receiver_id' not in request.session:
        return JsonResponse({'error': 'Not authenticated'})
    
    receiver = Receiver.objects.get(receiver_id=request.session['receiver_id'])
    period = request.GET.get('period', 'month')
    
    end_date = timezone.now()
    if period == 'week':
        start_date = end_date - timedelta(days=7)
    elif period == 'month':
        start_date = end_date - timedelta(days=30)
    elif period == 'year':
        start_date = end_date - timedelta(days=365)
    else:
        start_date = receiver.created_at
    
    pickups = PickupSchedule.objects.filter(
        receiver_id=receiver,
        scheduled_time__gte=start_date,
        scheduled_time__lte=end_date
    )
    
    # Food type distribution - improved
    food_data = []
    accepted_pickups = pickups.filter(pickup_status='accepted')
    
    for pickup in accepted_pickups:
        food_type = pickup.donation_id.food_type
        quantity = pickup.donation_id.quantity
        
        # Check if this food type already exists in our list
        existing = next((item for item in food_data if item['food_type'] == food_type), None)
        if existing:
            existing['quantity'] += quantity
        else:
            food_data.append({'food_type': food_type, 'quantity': quantity})
    
    # Status distribution
    status_data = list(pickups.values('pickup_status').annotate(count=Count('pickup_status')))
    
    # Monthly trend - improved
    monthly_trend = []
    
    if period == 'year':
        for i in range(12):
            month_date = end_date.replace(day=1)
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
            
            month_pickups = pickups.filter(
                scheduled_time__gte=month_start,
                scheduled_time__lte=month_end
            )
            
            monthly_trend.append({
                'month': month_start.strftime('%b'),
                'total': month_pickups.count(),
                'successful': month_pickups.filter(pickup_status='accepted').count()
            })
        
        monthly_trend.reverse()
    
    # If no data but pickups exist, use sample data
  
    return JsonResponse({
        'food_data': food_data,
        'status_data': status_data,
        'monthly_trend': monthly_trend,
    })