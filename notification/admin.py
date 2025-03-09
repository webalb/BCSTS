from django.contrib import admin
from notification.models import Notification

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'heading', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('user__email', 'heading', 'message')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)

    actions = ['mark_as_read']

    def mark_as_read(self, request, queryset):
        """Mark selected notifications as read."""
        queryset.update(is_read=True)
    mark_as_read.short_description = "Mark selected notifications as read"

