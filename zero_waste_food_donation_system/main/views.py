from django.shortcuts import render, redirect
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.hashers import check_password
from core.models import Donor, Receiver


def home(request):
    return render(request, 'home.html')


def dashboard(request):
    if 'donor_id' in request.session:
        return redirect('donors:dashboard')
    elif 'receiver_id' in request.session:
        return redirect('receivers:dashboard')
    return redirect('main:auth')


def profile(request):
    if 'donor_id' in request.session:
        return redirect('donors:profile')
    elif 'receiver_id' in request.session:
        return redirect('receivers:profile')
    return redirect('main:auth')


def auth(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        user_type = request.POST.get('user_type')
        if action == 'login':
            username = request.POST.get('username')
            password = request.POST.get('password')
            if user_type == 'donor':
                try:
                    donor = Donor.objects.get(name=username)
                    if check_password(password, donor.password):
                        request.session['donor_id'] = donor.donor_id
                        return redirect('donors:dashboard')
                except Donor.DoesNotExist:
                    pass
            elif user_type == 'receiver':
                try:
                    receiver = Receiver.objects.get(name=username)
                    if check_password(password, receiver.password):
                        request.session['receiver_id'] = receiver.receiver_id
                        return redirect('receivers:dashboard')
                except Receiver.DoesNotExist:
                    pass
    return render(request, 'auth.html', {
        'action': request.GET.get('action', 'login'),
        'user_type': request.GET.get('user_type', 'donor'),
        'active_tab': request.GET.get('action', 'login') == 'login' and 'login' or 'register'
    })


def logout_view(request):
    if 'donor_id' in request.session:
        del request.session['donor_id']
    if 'receiver_id' in request.session:
        del request.session['receiver_id']
    auth_logout(request)
    return redirect('main:home')
