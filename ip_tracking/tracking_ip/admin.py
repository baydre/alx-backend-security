from django.contrib import admin
from .models import RequestLog, BlockedIP, SuspiciousIP

@admin.register(RequestLog)
class RequestLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'ip_address', 'path', 'country', 'city')
    list_filter = ('country', 'city')
    search_fields = ('ip_address', 'path', 'country', 'city')
    readonly_fields = ('timestamp',) # Logs should not be editable

@admin.register(BlockedIP)
class BlockedIPAdmin(admin.ModelAdmin):
    list_display = ('ip_address', 'created_at')
    search_fields = ('ip_address',)

@admin.register(SuspiciousIP)
class SuspiciousIPAdmin(admin.ModelAdmin):
    list_display = ('ip_address', 'reason', 'flagged_at')
    list_filter = ('reason',)
    search_fields = ('ip_address', 'reason')
