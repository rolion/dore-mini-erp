from .base import *  # noqa: F401,F403
from .base import env

# PostgreSQL real también en tests (regla del proyecto: sin SQLite).
DEBUG = False
SECRET_KEY = env('SECRET_KEY', default='insecure-test-key-not-for-production')
ALLOWED_HOSTS = ['testserver', 'localhost']
DATABASES = {'default': env.db('DATABASE_URL')}
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
