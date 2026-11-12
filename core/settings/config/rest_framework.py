REST_FRAMEWORK = {
    # 'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    # 'PAGE_SIZE': 20,  # har sahifada 20 ta (siz xohlaganingizcha o'zgartiring)
    # 'PAGE_SIZE_QUERY_PARAM': 'page_size',  # ?page_size=50 deb o'zgartirish mumkin
    # # 'MAX_PAGE_SIZE': 100,  # maksimal 100 ta
    #
    # "DEFAULT_FILTER_BACKENDS": [
    #     "django_filters.rest_framework.DjangoFilterBackend",
    #     "rest_framework.filters.SearchFilter",
    # ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'EXCEPTION_HANDLER': 'apps.common.exception_handler.custom_exception_handler',
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    # BasicAuthentication olib tashlandi: cookie/JWT sxemasida ishlatilmaydi,
    # lekin har bir endpointda throttling'siz parol taxmin qilish yuzasini ochardi.
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.users.api.auth.authentication.CookieJWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
        # "rest_framework_simplejwt.authentication.JWTAuthentication",

    ],
    # Throttling global tarzda yoqilmaydi (biznes API'lariga xalal bermaslik uchun).
    # Faqat auth endpointlar (login, forgot-password, reset-password) o'z view'larida
    # throttle_classes orqali cheklanadi.
    'DEFAULT_THROTTLE_RATES': {
        'login_ip': '10/min',
        'login_identifier': '5/min',
        'password_reset_request_ip': '10/hour',
        'password_reset_request_email': '3/hour',
        'password_reset_confirm': '5/min',
        'otp_resend': '3/min',
        'public_inquiry': '5/hour',
    },
}


SPECTACULAR_SETTINGS = {
    'TITLE': 'CU Grande Education',
    'DESCRIPTION': 'CU Grande Education — ta’lim platformasi uchun backend API.',
    'VERSION': '1.0.0',
    'OAS_VERSION': '3.1.0',
    'SERVE_INCLUDE_SCHEMA': False,
}
