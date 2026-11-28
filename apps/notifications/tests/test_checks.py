from django.test import SimpleTestCase, override_settings

from apps.notifications.checks import check_channel_layer_redis_db


def _layers(url):
    return {"default": {"BACKEND": "channels_redis.core.RedisChannelLayer", "CONFIG": {"hosts": [url]}}}


class ChannelLayerRedisCheckTests(SimpleTestCase):
    @override_settings(
        CHANNEL_LAYERS=_layers("redis://127.0.0.1:6379/3"),
        CELERY_BROKER_URL="redis://127.0.0.1:6379/2",
        CACHES={"default": {"BACKEND": "django.core.cache.backends.redis.RedisCache",
                            "LOCATION": "redis://127.0.0.1:6379/1"}},
    )
    def test_separate_db_passes(self):
        self.assertEqual(check_channel_layer_redis_db(None), [])

    @override_settings(
        CHANNEL_LAYERS=_layers("redis://localhost:6379/2"),
        CELERY_BROKER_URL="redis://localhost:6379/2",
    )
    def test_same_db_as_celery_warns(self):
        warnings = check_channel_layer_redis_db(None)
        self.assertEqual([w.id for w in warnings], ["notifications.W001"])

    @override_settings(
        CHANNEL_LAYERS=_layers("redis://127.0.0.1:6379/1"),
        CELERY_BROKER_URL="amqp://guest@localhost//",
        CACHES={"default": {"BACKEND": "django.core.cache.backends.redis.RedisCache",
                            "LOCATION": "redis://127.0.0.1:6379/1"}},
    )
    def test_same_db_as_cache_warns(self):
        self.assertEqual(len(check_channel_layer_redis_db(None)), 1)
