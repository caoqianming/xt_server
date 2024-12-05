from django.contrib.auth.backends import ModelBackend
from django.db.models import Q
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError

UserModel = get_user_model()

def get_user_by_username_or(username: str):
    try:
        user = UserModel._default_manager.get(
            Q(username=username) | Q(phone=username) | Q(employee__id_number=username))
        return user, ""
    except UserModel.DoesNotExist:
        return None, 'not_exist'
    except Exception as e:
        return None, str(e)

class CustomBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)
        if username is None or password is None:
            return
        user, msg = get_user_by_username_or(username)
        if msg == 'not_exist':
            UserModel().set_password(password)
        if user:
            key_login_attempt = f"login_attempt_{user.id}"
            if user.check_password(password) and self.user_can_authenticate(user):
                cache.delete(key_login_attempt)
                return user
            else:
                login_attempt = cache.get(key_login_attempt, 0)
                cache.set(key_login_attempt, login_attempt + 1, 60)

