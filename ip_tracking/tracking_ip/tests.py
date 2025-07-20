from django.test import TestCase, RequestFactory, override_settings
from django.core.cache import cache
from unittest.mock import patch, MagicMock
import geoip2.errors
from tracking_ip.models import RequestLog, BlockedIP
from tracking_ip.middleware import BasicIPLoggingMiddleware
import json


class IPGeolocationAnalyticsTestCase(TestCase):
    """
    Comprehensive test suite for IP geolocation analytics feature.
    Tests IP extraction, geolocation data fetching, database storage, and Redis caching.
    """
    
    def setUp(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()
        self.middleware = BasicIPLoggingMiddleware(lambda request: None)
        
        # Clear cache before each test
        cache.clear()
        
        # Clear existing RequestLog entries
        RequestLog.objects.all().delete()
        BlockedIP.objects.all().delete()
    
    def test_ip_extraction_from_remote_addr(self):
        """
        Test that IP addresses are correctly extracted from REMOTE_ADDR.
        """
        request = self.factory.get('/', REMOTE_ADDR='8.8.8.8')
        
        with patch('tracking_ip.middleware._geoip_reader') as mock_reader:
            # Mock successful geolocation
            mock_response = MagicMock()
            mock_response.country.name = 'United States'
            mock_response.city.name = 'Mountain View'
            mock_reader.city.return_value = mock_response
            
            self.middleware.process_request(request)
        
        # Verify RequestLog was created with correct IP
        log_entry = RequestLog.objects.get()
        self.assertEqual(log_entry.ip_address, '8.8.8.8')
        self.assertEqual(log_entry.path, '/')
        self.assertEqual(log_entry.country, 'United States')
        self.assertEqual(log_entry.city, 'Mountain View')
    
    def test_ip_extraction_with_ipware(self):
        """
        Test IP extraction using django-ipware with X-Forwarded-For header.
        """
        request = self.factory.get(
            '/api/test', 
            HTTP_X_FORWARDED_FOR='203.0.113.195, 70.41.3.18, 150.172.238.178',
            REMOTE_ADDR='127.0.0.1'
        )
        
        with patch('tracking_ip.middleware._geoip_reader') as mock_reader:
            # Mock successful geolocation for the real IP
            mock_response = MagicMock()
            mock_response.country.name = 'Australia'
            mock_response.city.name = 'Sydney'
            mock_reader.city.return_value = mock_response
            
            self.middleware.process_request(request)
        
        # Verify RequestLog was created with the forwarded IP
        log_entry = RequestLog.objects.get()
        self.assertEqual(log_entry.ip_address, '203.0.113.195')  # First IP in X-Forwarded-For
        self.assertEqual(log_entry.path, '/api/test')
        self.assertEqual(log_entry.country, 'Australia')
        self.assertEqual(log_entry.city, 'Sydney')
    
    def test_geolocation_caching_in_redis(self):
        """
        Test that geolocation data is properly cached in Redis.
        """
        test_ip = '1.2.3.4'
        request = self.factory.get('/', REMOTE_ADDR=test_ip)
        
        with patch('tracking_ip.middleware._geoip_reader') as mock_reader:
            # Mock successful geolocation
            mock_response = MagicMock()
            mock_response.country.name = 'Japan'
            mock_response.city.name = 'Tokyo'
            mock_reader.city.return_value = mock_response
            
            # First request - should hit GeoIP2 database
            self.middleware.process_request(request)
            mock_reader.city.assert_called_once_with(test_ip)
        
        # Verify cache was populated
        cache_key = f"geolocation:{test_ip}"
        cached_data = cache.get(cache_key)
        self.assertIsNotNone(cached_data)
        self.assertEqual(cached_data['country'], 'Japan')
        self.assertEqual(cached_data['city'], 'Tokyo')
        
        # Second request - should use cache
        with patch('tracking_ip.middleware._geoip_reader') as mock_reader:
            self.middleware.process_request(request)
            # Should not call GeoIP2 reader since data is cached
            mock_reader.city.assert_not_called()
        
        # Verify both requests created database entries
        log_entries = RequestLog.objects.filter(ip_address=test_ip)
        self.assertEqual(log_entries.count(), 2)
        
        for entry in log_entries:
            self.assertEqual(entry.country, 'Japan')
            self.assertEqual(entry.city, 'Tokyo')
    
    def test_geolocation_address_not_found(self):
        """
        Test behavior when IP address is not found in GeoIP database.
        """
        test_ip = '192.168.1.1'  # Private IP, not in GeoIP database
        request = self.factory.get('/private', REMOTE_ADDR=test_ip)
        
        with patch('tracking_ip.middleware._geoip_reader') as mock_reader:
            # Mock AddressNotFoundError
            mock_reader.city.side_effect = geoip2.errors.AddressNotFoundError("IP address not found")
            
            self.middleware.process_request(request)
        
        # Verify RequestLog was created without geolocation data
        log_entry = RequestLog.objects.get()
        self.assertEqual(log_entry.ip_address, test_ip)
        self.assertEqual(log_entry.path, '/private')
        self.assertIsNone(log_entry.country)
        self.assertIsNone(log_entry.city)
    
    def test_geolocation_reader_not_initialized(self):
        """
        Test behavior when GeoIP2 reader is not initialized.
        """
        test_ip = '5.6.7.8'
        request = self.factory.get('/test', REMOTE_ADDR=test_ip)
        
        with patch('tracking_ip.middleware._geoip_reader', None):
            self.middleware.process_request(request)
        
        # Verify RequestLog was created without geolocation data
        log_entry = RequestLog.objects.get()
        self.assertEqual(log_entry.ip_address, test_ip)
        self.assertEqual(log_entry.path, '/test')
        self.assertIsNone(log_entry.country)
        self.assertIsNone(log_entry.city)
    
    def test_ip_blocking_functionality(self):
        """
        Test that blocked IPs are properly handled.
        """
        blocked_ip = '10.0.0.1'
        # Add IP to blocked list
        BlockedIP.objects.create(ip_address=blocked_ip)
        
        request = self.factory.get('/blocked', REMOTE_ADDR=blocked_ip)
        
        response = self.middleware.process_request(request)
        
        # Should return HttpResponseForbidden
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.content.decode(), "You are blocked.")
        
        # Verify no RequestLog was created for blocked IP
        self.assertEqual(RequestLog.objects.filter(ip_address=blocked_ip).count(), 0)
    
    def test_cache_expiration_and_refresh(self):
        """
        Test that cache expires and data is refreshed from GeoIP2 database.
        """
        test_ip = '9.10.11.12'
        request = self.factory.get('/', REMOTE_ADDR=test_ip)
        cache_key = f"geolocation:{test_ip}"
        
        with patch('tracking_ip.middleware._geoip_reader') as mock_reader:
            # Mock first geolocation response
            mock_response = MagicMock()
            mock_response.country.name = 'Canada'
            mock_response.city.name = 'Toronto'
            mock_reader.city.return_value = mock_response
            
            self.middleware.process_request(request)
        
        # Manually expire the cache entry
        cache.delete(cache_key)
        
        with patch('tracking_ip.middleware._geoip_reader') as mock_reader:
            # Mock updated geolocation response
            mock_response = MagicMock()
            mock_response.country.name = 'Canada'
            mock_response.city.name = 'Vancouver'
            mock_reader.city.return_value = mock_response
            
            self.middleware.process_request(request)
            # Should call GeoIP2 reader again since cache was cleared
            mock_reader.city.assert_called_once_with(test_ip)
        
        # Verify new data is cached
        cached_data = cache.get(cache_key)
        self.assertEqual(cached_data['city'], 'Vancouver')
    
    def test_database_storage_integrity(self):
        """
        Test that all request data is properly stored in the database.
        """
        test_cases = [
            ('198.51.100.1', '/api/users', 'Germany', 'Berlin'),
            ('203.0.113.50', '/api/products', 'Singapore', 'Singapore'),
            ('192.0.2.100', '/dashboard', None, None),  # No geolocation data
        ]
        
        for ip, path, country, city in test_cases:
            request = self.factory.get(path, REMOTE_ADDR=ip)
            
            with patch('tracking_ip.middleware._geoip_reader') as mock_reader:
                if country and city:
                    mock_response = MagicMock()
                    mock_response.country.name = country
                    mock_response.city.name = city
                    mock_reader.city.return_value = mock_response
                else:
                    mock_reader.city.side_effect = geoip2.errors.AddressNotFoundError("IP address not found")
                
                self.middleware.process_request(request)
        
        # Verify all entries were created
        self.assertEqual(RequestLog.objects.count(), 3)
        
        # Verify each entry has correct data
        for ip, path, country, city in test_cases:
            log_entry = RequestLog.objects.get(ip_address=ip, path=path)
            self.assertEqual(log_entry.country, country)
            self.assertEqual(log_entry.city, city)
            self.assertIsNotNone(log_entry.timestamp)
    
    def test_concurrent_requests_caching(self):
        """
        Test cache behavior with multiple concurrent requests to same IP.
        """
        test_ip = '13.14.15.16'
        paths = ['/page1', '/page2', '/page3']
        
        with patch('tracking_ip.middleware._geoip_reader') as mock_reader:
            mock_response = MagicMock()
            mock_response.country.name = 'Brazil'
            mock_response.city.name = 'São Paulo'
            mock_reader.city.return_value = mock_response
            
            # Simulate multiple requests from same IP
            for path in paths:
                request = self.factory.get(path, REMOTE_ADDR=test_ip)
                self.middleware.process_request(request)
        
        # Should only call GeoIP2 reader once (first request)
        self.assertEqual(mock_reader.city.call_count, 1)
        
        # All three requests should be logged with geolocation data
        log_entries = RequestLog.objects.filter(ip_address=test_ip)
        self.assertEqual(log_entries.count(), 3)
        
        for entry in log_entries:
            self.assertEqual(entry.country, 'Brazil')
            self.assertEqual(entry.city, 'São Paulo')
    
    def tearDown(self):
        """Clean up after tests."""
        cache.clear()
