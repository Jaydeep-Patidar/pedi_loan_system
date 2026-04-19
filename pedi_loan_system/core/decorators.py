from django.shortcuts import redirect
from django.contrib import messages

def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if hasattr(request.user, 'member_profile'):
            if request.user.member_profile.role == 'admin':
                return view_func(request, *args, **kwargs)
        messages.error(request, 'Admin access required')
        return redirect('dashboard')
    return wrapper

def member_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if hasattr(request.user, 'member_profile'):
            if request.user.member_profile.role == 'member':
                return view_func(request, *args, **kwargs)
        messages.error(request, 'Member access required')
        return redirect('dashboard')
    return wrapper