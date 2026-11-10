THIRD_PARTY_APPS = [
    "corsheaders",
    "rest_framework",
    "drf_spectacular",
    # 'rest_framework_simplejwt',
    # ishlatilgan refresh tokenlar qora ro'yxatga tushadi.
    # 'rest_framework_simplejwt.token_blacklist',
]

DEFAULT_APPS = [
    'jazzmin',
    # 'modeltranslation',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

LOCAL_APPS = [
    "apps.users",
    "apps.rbac",
    "apps.universities",
]
