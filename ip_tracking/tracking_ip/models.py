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

    class Meta:
        verbose_name = "Request Log"
        verbose_name_plural = "Request Logs"
        ordering = ['-timestamp'] # Order by most recent first

    def __str__(self):
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] {self.ip_address} - {self.path}"


class BlockedIP(models.Model):
    """
    Model to store IP addresses that should be blocked.
    """
    ip_address = models.GenericIPAddressField(
        unique=True, # Ensure each IP is unique in the blacklist
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
