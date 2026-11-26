from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']

# Lokal dev origin'lari (vite 5173 / preview 4173). "Hamma origin" ruxsati
# bu yerda ham berilmaydi: credentials bilan birga u istalgan saytga dev
# serveridagi ma'lumotni o'qish imkonini berardi.
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
    "http://localhost:3000",
]
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# EXPIRE_TIME = 1
#
FRONTEND_URL = config(
    "FRONTEND_URL",
    default="http://localhost:3000",
)

# # Lokal muhitda Redis talab qilinmasin — WS bildirishnomalar InMemory qatlamda ishlaydi
# CHANNEL_LAYERS = {
#     "default": {
#         "BACKEND": "channels.layers.InMemoryChannelLayer",  # dev
#     }
# }

AUTH_COOKIE_SECURE = False
AUTH_COOKIE_SAMESITE = "Lax"


CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
        "KEY_PREFIX": "cu_grande_dev",
        "TIMEOUT": 300,
    }
}