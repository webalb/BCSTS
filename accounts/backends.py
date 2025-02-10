# In your app (e.g., accounts/backends.py):

from django.contrib.auth.backends import ModelBackend
from .models import CustomUser  # Your custom user model

class EmailAuthBackend(ModelBackend):
    def authenticate(self, request, email=None, password=None, **kwargs):
        if email and password:
            try:
                user = CustomUser.objects.get(email=email)
                if user.check_password(password):
                    return user
            except CustomUser.DoesNotExist:
                return None  # Important: Return None if user not found

    def get_user(self, user_id):
        try:
            return CustomUser.objects.get(pk=user_id)
        except CustomUser.DoesNotExist:
            return None