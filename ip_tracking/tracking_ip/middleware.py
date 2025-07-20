from tracking_ip.models import RequestLog, BlockedIP
from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponseForbidden
from ipware import get_client_ip
import geoip2.database
from django.conf import settings
from django.core.cache import cache
import logging
import os

logger = logging.getLogger(__name__)

# Global GeoIP2 reader instance (initialized once)
_geoip_reader = None
try:
    # Check if GEOIP_PATH is configured and file exists
    if hasattr(settings, 'GEOIP_PATH') and settings.GEOIP_PATH and \
       os.path.exists(settings.GEOIP_PATH):
        _geoip_reader = geoip2.database.Reader(settings.GEOIP_PATH)
    else:
        logger.warning(
            "GEOIP_PATH not configured or GeoLite2-City.mmdb not found. "
            "Geolocation will be skipped.")
except Exception as e:
    logger.error(f"Error initializing GeoIP2 reader: {e}", exc_info=True)
    _geoip_reader = None # Ensure it's None if initialization fails


class BasicIPLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log and block IP addresses.
    Uses django-ipware for IP, geoip2 for location,
    and Django cache for caching lookups.
    """
    def process_request(self, request):
        """
        Process the request to log IP details and block malicious IPs,
        and geolocate.
        """
        ip_address, _ = get_client_ip(request)
        if ip_address is None:
            ip_address = request.META.get('REMOTE_ADDR', 'unknown')
            logger.warning(f"Could not determine client IP with ipware, "
                          f"falling back to REMOTE_ADDR: {ip_address}")

        if ip_address and ip_address != 'unknown':
            # --- IP Blacklisting Logic ---
            if BlockedIP.objects.filter(ip_address=ip_address).exists():
                logger.warning(
                    f"Blocked request from blacklisted IP: {ip_address}"
                )
                return HttpResponseForbidden("You are blocked.")

            # --- Geolocation Logic ---
            country = None
            city = None
            geolocation_cache_key = f"geolocation:{ip_address}"
            # Try to get geolocation from cache first
            cached_geo_data = cache.get(geolocation_cache_key)

            if cached_geo_data:
                country = cached_geo_data.get('country')
                city = cached_geo_data.get('city')
                # logger.debug(f"Geolocation from cache for {ip_address}: {city}, {country}")
            elif _geoip_reader:
                try:
                    # Perform geolocation lookup if not in cache
                    response = _geoip_reader.city(ip_address)
                    country = response.country.name
                    city = response.city.name
                    # Cache the result for 24 hours (86400 seconds)
                    cache.set(geolocation_cache_key, {'country': country, 'city': city}, 86400)
                    # logger.debug(f"Geolocation from GeoIP2 for {ip_address}: {city}, {country}")
                except geoip2.errors.AddressNotFoundError:
                    logger.debug(f"Geolocation: IP address {ip_address} not found in database.")
                except Exception as e:
                    logger.error(f"Error during GeoIP2 lookup for {ip_address}: {e}", exc_info=True)
            else:
                logger.debug(f"Skipping geolocation for {ip_address}: GeoIP2 reader not initialized.")
            
            # --- Basic IP Logging Logic (from Task 0) ---
            path = request.path
            try:
                RequestLog.objects.create(
                    ip_address=ip_address,
                    path=path,
                    country=country,
                    city=city
                )
                # logger.info(f"Logged request: IP={ip_address}, Path={path},
                # Country={country}, City={city}")
            except Exception as e:
                logger.error(f"Error logging request: {e}", exc_info=True)
        return None
