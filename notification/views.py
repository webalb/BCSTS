from django.http import JsonResponse
from .models import Notification

def notifications_api(request):
    notifications = Notification.objects.filter(user=request.user, is_read=False).order_by('-created_at')[:5]
    data = [
        {
            "heading": n.heading,
            "message": n.message,
            "link": n.link,
            "created_at": n.created_at.strftime("%Y-%m-%d %H:%M:%S")
        } 
        for n in notifications
    ]
    return JsonResponse(data, safe=False)