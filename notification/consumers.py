import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from .models import Notification

class DashboardConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """Handles user connection to WebSocket"""
        self.user = self.scope["user"]

        if self.user.is_authenticated:
            self.group_name = f"user_{self.user.id}"
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()

            # Send unread notifications on connection
            unread_notifications = await self.get_unread_notifications()
            await self.send(text_data=json.dumps({
                "event_type": "notification",
                "notifications": unread_notifications
            }))
        else:
            await self.close()

    async def disconnect(self, close_code):
        """Removes user from WebSocket group on disconnect"""
        if self.user.is_authenticated:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        """Handles messages from the frontend"""
        data = json.loads(text_data)
        event_type = data.get("event_type")

        if event_type == "mark_as_read":
            notification_id = data.get("notification_id")
            if notification_id:
                await self.mark_notification_as_read(notification_id)

    async def send_notification(self, event):
        """Sends real-time notifications to users"""
        await self.send(text_data=json.dumps({
            "event_type": "notification",
            "notifications": [event["notification"]]
        }))

    @sync_to_async
    def get_unread_notifications(self):
        """Fetch unread notifications for the user"""
        return [
            {
                "id": n.id,
                "heading": n.heading,
                "message": n.message,
                "link": n.link,
                "created_at": str(n.created_at),
                "is_read": n.is_read
            }
            for n in Notification.objects.filter(user=self.user, is_read=False).order_by("-created_at")
        ]

    @sync_to_async
    def mark_notification_as_read(self, notification_id):
        """Marks a notification as read"""
        Notification.objects.filter(id=notification_id, user=self.user).update(is_read=True)
