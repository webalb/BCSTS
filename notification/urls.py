from django.urls import path
from .views import get_notifications, mark_notification_as_read, mark_all_notifications_as_read

urlpatterns = [
    path("get/", get_notifications, name="get_notifications"),
    path("mark-as-read/<int:notification_id>/", mark_notification_as_read, name="mark_notification_as_read"),
    path('mark-all-as-read/', mark_all_notifications_as_read, name='mark_all_notifications_as_read'),
]
