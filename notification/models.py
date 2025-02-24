from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from accounts.models import CustomUser

class Notification(models.Model):
    class NotificationType(models.TextChoices):
        EMAIL = 'email', _('Email')
        IN_APP = 'in_app', _('In-App')

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='notifications')
    heading = models.CharField(max_length=255)  # Subject of the notification
    message = models.TextField(blank=True, null=True)  # Optional message body
    link = models.URLField(blank=True, null=True)  # URL to the related action/page
    notification_type = models.CharField(max_length=10, choices=NotificationType.choices, default=NotificationType.IN_APP)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.heading} - {self.notification_type} - {'Read' if self.is_read else 'Unread'}"
