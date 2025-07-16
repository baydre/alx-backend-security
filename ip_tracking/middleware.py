from ip_tracking.models import RequestLog # Import your model
from django.utils.deprecation import MiddlewareMixin
import logging

logger = logging.getLogger(__name__)

class BasicIPLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log the IP address, timestamp, and path of every incoming request.
    """
    def process_request(self, request):
        """
        Process the request to log IP details.
        """
        ip_address = request.META.get('REMOTE_ADDR')
        if ip_address:
            path = request.path
            try:
                RequestLog.objects.create(
                    ip_address=ip_address,
                    path=path
                )
                # logger.info(f"Logged request: IP={ip_address}, Path={path}")
            except Exception as e:
                logger.error(f"Error logging request: {e}", exc_info=True)
        return None # Must return None or an HttpResponse object
