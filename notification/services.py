from .models import Notification

class NotificationService:
    @staticmethod
    def send_notification(user, heading, message=None, link=None, notification_type='in_app'):
        """
        Sends a notification to the user based on the selected type.
        """
        notification = Notification.objects.create(
            user=user,
            heading=heading,
            message=message,
            link=link,
            notification_type=notification_type
        )


    