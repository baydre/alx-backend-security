from celery import shared_task
from tracking_ip.models import RequestLog, SuspiciousIP
from django.db.models import Count
from datetime import timedelta
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

@shared_task
def detect_anomalies():
    """
    Celery task to detect suspicious IP addresses based on request patterns.
    Flags IPs exceeding 100 requests/hour or accessing sensitive paths.
    """
    logger.info("Starting anomaly detection task...")
    now = timezone.now()
    one_hour_ago = now - timedelta(hours=1)

    # Rule 1: IPs exceeding 100 requests/hour
    high_traffic_ips = RequestLog.objects.filter(
        timestamp__gte=one_hour_ago
    ).values('ip_address').annotate(
        request_count=Count('ip_address')
    ).filter(request_count__gt=100)

    for item in high_traffic_ips:
        ip_address = item['ip_address']
        reason = f"Exceeded 100 requests ({item['request_count']}) in the last hour."
        SuspiciousIP.objects.get_or_create(ip_address=ip_address, defaults={'reason': reason})
        logger.warning(f"Flagged suspicious IP (high traffic): {ip_address}")

    # Rule 2: IPs accessing sensitive paths frequently
    sensitive_paths = ['/admin/', '/login/', '/api/v1/sensitive_data/'] # Define your sensitive paths
    for path in sensitive_paths:
        sensitive_access_ips = RequestLog.objects.filter(
            timestamp__gte=one_hour_ago,
            path__startswith=path # Use startswith for paths like /admin/login etc.
        ).values('ip_address').annotate(
            access_count=Count('ip_address')
        ).filter(access_count__gt=5) # Example: more than 5 accesses to sensitive path in an hour

        for item in sensitive_access_ips:
            ip_address = item['ip_address']
            reason = f"Accessed sensitive path '{path}' {item['access_count']} times in the last hour."
            # Append reason if IP already flagged, or create new
            suspicious_ip, created = SuspiciousIP.objects.get_or_create(
                ip_address=ip_address,
                defaults={'reason': reason}
            )
            if not created:
                # If already exists, update reason to include new flag
                if reason not in suspicious_ip.reason: # Avoid duplicate reasons
                    suspicious_ip.reason += f"; {reason}"
                    suspicious_ip.save()
            logger.warning(f"Flagged suspicious IP (sensitive path access): {ip_address}")

    logger.info("Anomaly detection task completed.")
