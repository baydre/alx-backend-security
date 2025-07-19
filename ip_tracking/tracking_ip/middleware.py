from ip_tracking.models import RequestLog, BlockedIP # Import new model
from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponseForbidden # Import for 403 response
import logging

logger = logging.getLogger(__name__)

class BasicIPLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log and block IP addresses.
    """
    def process_request(self, request):
        """
        Process the request to log IP details and block malicious IPs.
        """
        ip_address = request.META.get('REMOTE_ADDR')

        if ip_address:
            # --- IP Blacklisting Logic ---
            if BlockedIP.objects.filter(ip_address=ip_address).exists():
                logger.warning(f"Blocked request from blacklisted IP: {ip_address}")
                return HttpResponseForbidden("You are blocked.") # Return 403 Forbidden

            # --- Basic IP Logging Logic (from Task 0) ---
            path = request.path
            try:
                RequestLog.objects.create(
                    ip_address=ip_address,
                    path=path
                )
                # logger.info(f"Logged request: IP={ip_address}, Path={path}")
            except Exception as e:
                logger.error(f"Error logging request: {e}", exc_info=True)
        return None # Continue processing if not blocked
