from django.core.mail import send_mail
from django.conf import settings
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json
from .models import Notification

class NotificationService:
    @staticmethod
    def send_notification(user, heading, message=None, link=None, notification_type='in_app'):
        """
        Sends a notification to the user based on the selected type.
        """
        if notification_type == Notification.NotificationType.EMAIL:
            NotificationService.send_email(user.email, heading, message or "", link)
        
        # Save in-app notification to the database
        notification = Notification.objects.create(
            user=user,
            heading=heading,
            message=message,
            link=link,
            notification_type=notification_type
        )

        # Send WebSocket notification
        NotificationService.send_websocket_notification(user, notification)

    @staticmethod
    def send_email(email, subject, message, link=None):
        """
        Sends an email notification.
        """
        full_message = f"{message}\n\nView more: {link}" if link else message
        send_mail(
            subject,
            full_message,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )

    @staticmethod
    def send_websocket_notification(user, notification):
        """
        Sends real-time WebSocket notifications.
        """
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"user_{user.id}",
            {
                "type": "send_notification",
                "notification": {
                    "id": notification.id,
                    "heading": notification.heading,
                    "message": notification.message,
                    "link": notification.link,
                    "created_at": str(notification.created_at),
                    "is_read": notification.is_read
                }
            }
        )
