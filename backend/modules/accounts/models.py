from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """Usuario propio mínimo; permite extenderlo sin migrar auth.User después."""
