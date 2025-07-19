# ip_tracking/management/commands/block_ip.py
from django.core.management.base import BaseCommand, CommandError
from tracking_ip.models import BlockedIP
import ipaddress # For IP validation

class Command(BaseCommand):
    """
    Django management command to add an IP address to the blacklist.
    Usage: python manage.py block_ip <ip_address>
    """
    help = 'Blocks a given IP address.'

    def add_arguments(self, parser):
        """
        Add arguments to the command parser.
        """
        parser.add_argument('ip_address', type=str, help='The IP address to block.')

    def handle(self, *args, **options):
        """
        Handle the command execution.
        """
        ip_address = options['ip_address']

        # Validate IP address format
        try:
            ipaddress.ip_address(ip_address) # Checks if it's a valid IPv4 or IPv6
        except ValueError:
            raise CommandError(f"'{ip_address}' is not a valid IP address.")

        # Check if IP is already blocked
        if BlockedIP.objects.filter(ip_address=ip_address).exists():
            self.stdout.write(self.style.WARNING(f"IP address '{ip_address}' is already blocked."))
            return

        # Add IP to blacklist
        try:
            BlockedIP.objects.create(ip_address=ip_address)
            self.stdout.write(self.style.SUCCESS(f"Successfully blocked IP address: '{ip_address}'"))
        except Exception as e:
            raise CommandError(f"Error blocking IP address '{ip_address}': {e}")
