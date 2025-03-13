from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
import pytz
from .models import Notification

@login_required
def get_notifications(request):
    notifications = Notification.objects.filter(user=request.user, is_read=False).order_by("created_at")[:10]
    local_tz = pytz.timezone('Africa/Lagos')  # Change to 'Africa/Abuja' if preferred
    data = [
        {
            "id": n.id,
            "heading": n.heading,
            "message": n.message,
            "link": n.link,
            "created_at": n.created_at.astimezone(local_tz).strftime("%Y-%m-%d %H:%M:%S"),
            "is_read": n.is_read
        }
        for n in notifications
    ]
    return JsonResponse({"notifications": data})

@csrf_exempt
@login_required
def mark_notification_as_read(request, notification_id):
    if not request.user.is_authenticated:
        return JsonResponse({"success": False, "error": "User not authenticated"}, status=401)  # Return JSON instead of redirecting

    try:
        notification = get_object_or_404(Notification, id=notification_id, user=request.user)
        notification.is_read = True
        notification.save()
        return JsonResponse({"success": True})
    except Notification.DoesNotExist:
        return JsonResponse({"success": False, "error": "Notification not found"}, status=404)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)

@csrf_exempt
@login_required
def mark_all_notifications_as_read(request):
    if request.user.is_authenticated:
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return JsonResponse({"success": True})
    return JsonResponse({"success": False})
