from django.core.management.base import BaseCommand
from django.test import RequestFactory
from tracking_ip.middleware import BasicIPLoggingMiddleware
from tracking_ip.models import RequestLog
import time


class Command(BaseCommand):
    help = 'Test geolocation functionality with real external IP addresses'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing RequestLog entries before testing',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing RequestLog entries...')
            RequestLog.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Cleared all RequestLog entries'))

        # Test IP addresses from different countries with known locations
        test_ips = [
            ('8.8.8.8', 'United States', 'Google DNS'),
            ('208.67.222.222', 'United States', 'OpenDNS'),
            ('1.1.1.1', 'Australia', 'Cloudflare DNS'),
            ('185.228.168.9', 'Germany', 'CleanBrowsing DNS'),
            ('76.76.19.19', 'United States', 'Alternate DNS'),
            ('94.140.14.14', 'Czech Republic', 'AdGuard DNS'),
            ('156.154.70.1', 'United States', 'Neustar DNS'),
            ('77.88.8.8', 'Russia', 'Yandex DNS'),
        ]

        factory = RequestFactory()
        middleware = BasicIPLoggingMiddleware(lambda request: None)

        self.stdout.write('Testing geolocation with real external IP addresses...\n')

        for ip, expected_country, description in test_ips:
            self.stdout.write(f'Testing {ip} ({description})...')
            
            # Create a fake request with the test IP
            request = factory.get('/test-geolocation', REMOTE_ADDR=ip)
            
            # Process the request through middleware
            try:
                middleware.process_request(request)
                
                # Fetch the created log entry
                log_entry = RequestLog.objects.filter(ip_address=ip).last()
                if log_entry:
                    self.stdout.write(
                        f'  ✓ IP: {log_entry.ip_address}'
                    )
                    self.stdout.write(
                        f'  ✓ Country: {log_entry.country or "Not found"}'
                    )
                    self.stdout.write(
                        f'  ✓ City: {log_entry.city or "Not found"}'
                    )
                    self.stdout.write(
                        f'  ✓ Path: {log_entry.path}'
                    )
                    self.stdout.write(
                        f'  ✓ Timestamp: {log_entry.timestamp}'
                    )
                else:
                    self.stdout.write(self.style.ERROR('  ✗ No log entry created'))
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  ✗ Error processing {ip}: {e}')
                )
            
            self.stdout.write('')  # Empty line for readability
            time.sleep(0.5)  # Small delay to avoid overwhelming the GeoIP database

        # Summary
        total_logs = RequestLog.objects.count()
        logs_with_geolocation = RequestLog.objects.exclude(
            country__isnull=True, city__isnull=True
        ).count()
        
        self.stdout.write(self.style.SUCCESS(f'\n=== SUMMARY ==='))
        self.stdout.write(f'Total logs created: {total_logs}')
        self.stdout.write(f'Logs with geolocation data: {logs_with_geolocation}')
        self.stdout.write(f'Logs without geolocation data: {total_logs - logs_with_geolocation}')
        
        if logs_with_geolocation > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    '\n✓ Geolocation is working! Check the Django admin interface to see city and country data.'
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    '\n⚠ No geolocation data was found. Check GeoIP database configuration.'
                )
            )
