THIRD_PARTY_APPS = [
    "corsheaders",
    "rest_framework",
    "drf_spectacular",
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
]

DEFAULT_APPS = [
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
]
