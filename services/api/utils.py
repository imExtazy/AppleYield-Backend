from django.contrib.auth.models import User


def _get_or_create_creator_user() -> User:
    user, _ = User.objects.get_or_create(username="demo", defaults={"email": "demo@example.com"})
    return user


def _get_or_create_moderator_user() -> User:
    user, _ = User.objects.get_or_create(username="admin123", defaults={"email": "admin123@example.com"})
    return user


