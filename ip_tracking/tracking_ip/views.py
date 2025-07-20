from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import models
from .models import RequestLog
from ipware import get_client_ip
import json


def index(request):
    """Simple index view to test IP tracking."""
    return render(request, 'tracking_ip/index.html')


def api_test(request):
    """API endpoint to test IP tracking."""
    ip_address, _ = get_client_ip(request)
    
    # Get recent logs for this IP
    recent_logs = RequestLog.objects.filter(ip_address=ip_address).order_by('-timestamp')[:5]
    
    logs_data = []
    for log in recent_logs:
        logs_data.append({
            'ip': log.ip_address,
            'path': log.path,
            'timestamp': log.timestamp.isoformat(),
            'country': log.country,
            'city': log.city
        })
    
    return JsonResponse({
        'client_ip': ip_address,
        'message': 'IP tracking test successful',
        'recent_requests': logs_data
    })


def geolocation_stats(request):
    """View to display geolocation statistics."""
    total_requests = RequestLog.objects.count()
    geolocated_requests = RequestLog.objects.exclude(
        country__isnull=True, city__isnull=True
    ).count()
    
    country_stats = RequestLog.objects.exclude(
        country__isnull=True
    ).values('country').annotate(
        count=models.Count('country')
    ).order_by('-count')
    
    return JsonResponse({
        'total_requests': total_requests,
        'geolocated_requests': geolocated_requests,
        'coverage_percentage': round((geolocated_requests / total_requests * 100), 2) if total_requests > 0 else 0,
        'top_countries': list(country_stats[:10])
    })
