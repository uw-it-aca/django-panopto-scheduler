from django.conf import settings
from uw_saml.utils import get_user
from scheduler.utils import person_from_username


def user(request):
    user_service = UserService()
    try:
        user = person_from_username(get_user(request))
        user_fullname = user.get_formatted_name(string_format="{first} {last}")
    except Exception as ex:
        user_fullname = None

    return {
        "user_login": user_service.get_user(),
        "user_fullname": user_fullname,
        "override_user": user_service.get_override_user(),
    }


def has_less_compiled(request):
    """ See if django-compressor is being used to precompile less
    """
    key = getattr(settings, "COMPRESS_PRECOMPILERS", None)
    return {"has_less_compiled": key != ()}


def debug_mode(request):
    return {"debug_mode": settings.DEBUG}
