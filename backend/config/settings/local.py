from .base import *  # noqa: F401,F403
from .base import env

# Desarrollo: DEBUG por defecto; SECRET_KEY solo de desarrollo si no se define en el entorno.
DEBUG = env.bool('DEBUG', default=True)
SECRET_KEY = env('SECRET_KEY', default='insecure-local-dev-key-not-for-production')
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])
DATABASES = {'default': env.db('DATABASE_URL')}
