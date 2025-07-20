from django.db import models

class RequestLog(models.Model):
    """
    Model to log details of incoming requests.
    """
    ip_address = models.GenericIPAddressField(
        verbose_name="IP Address",
        help_text="The IP address of the client."
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Timestamp",
        help_text="The time the request was made."
    )
    path = models.CharField(
        max_length=254,
        verbose_name="Request Path",
        help_text="The path of the requested URL."
    )

    country = models.CharField(
        max_length=100,
        blank=True, # Allow empty, as geolocation might fail or not be available
        null=True,
        verbose_name="Country",
        help_text="Country derived from IP geolocation."
    )
    city = models.CharField(
        max_length=100,
        blank=True, # Allow empty
        null=True,
        verbose_name="City",
        help_text="City derived from IP geolocation."
    )

    class Meta:
        verbose_name = "Request Log"
        verbose_name_plural = "Request Logs"
        ordering = ['-timestamp']

    def __str__(self):
        geo_info = f" ({self.city}, {self.country})" if self.city or self.country else ""
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] {self.ip_address}{geo_info} - {self.path}"


class BlockedIP(models.Model):
    """
    Model to store IP addresses that should be blocked.
    """
    ip_address = models.GenericIPAddressField(
        unique=True, 
        verbose_name="Blocked IP Address",
        help_text="The IP address to block."
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Blocked At",
        help_text="The time the IP was added to the blacklist."
    )

    class Meta:
        verbose_name = "Blocked IP"
        verbose_name_plural = "Blocked IPs"
        ordering = ['-created_at']

    def __str__(self):
        return self.ip_address


class SuspiciousIP(models.Model):
    """
    Model to store IP addresses flagged as suspicious.
    """
    ip_address = models.GenericIPAddressField(
        unique=True,
        verbose_name="Suspicious IP Address",
        help_text="The IP address flagged as suspicious."
    )
    reason = models.TextField(
        verbose_name="Reason for Flagging",
        help_text="Why this IP was flagged as suspicious."
    )
    flagged_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Flagged At",
        help_text="The time the IP was flagged."
    )
    # You could add more fields like 'is_blocked' or 'severity'

    class Meta:
        verbose_name = "Suspicious IP"
        verbose_name_plural = "Suspicious IPs"
        ordering = ['-flagged_at']

    def __str__(self):
        return f"{self.ip_address} - {self.reason}"
