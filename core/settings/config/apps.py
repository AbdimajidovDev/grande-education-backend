THIRD_PARTY_APPS = [
    "corsheaders",
    "channels",
    "rest_framework",
    "drf_spectacular",
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
]

DEFAULT_APPS = [
    # daphne staticfiles'dan oldin turishi kerak: `runserver` ASGI (HTTP + WS)
    # rejimida ishlaydi. Production'da HTTP baribir gunicorn orqali.
    'daphne',
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

LOCAL_APPS = [
    "apps.common.apps.CommonConfig",
    "apps.users",
    "apps.rbac",
    "apps.universities",
    "apps.inquiries",
    "apps.programs",
    "apps.partners",
    "apps.teachers",
    "apps.directions",
    "apps.site_settings",
    "apps.education_content",
    "apps.admissions.apps.AdmissionsConfig",
    "apps.dashboard",
    "apps.notifications.apps.NotificationsConfig",
]
