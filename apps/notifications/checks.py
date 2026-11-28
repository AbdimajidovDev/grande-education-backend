"""Redis channel layer konfiguratsiyasi uchun xavfsizlik tekshiruvi.

Redis'ga ulanmaydi — faqat sozlamalardagi URL'larni solishtiradi. Channel
layer cache yoki Celery broker bilan bir xil Redis DB'ni ishlatsa
ogohlantiradi (ma'lumotlar aralashmasligi uchun).
"""

from urllib.parse import urlparse

from django.conf import settings
from django.core.checks import Warning, register


def _redis_identity(url: str) -> tuple | None:
    if not isinstance(url, str) or not url.startswith(("redis://", "rediss://")):
        return None
    parsed = urlparse(url)
    db = (parsed.path or "/0").lstrip("/") or "0"
    return (parsed.hostname or "localhost", parsed.port or 6379, db)


def _channel_layer_urls() -> list[str]:
    urls = []
    for layer in getattr(settings, "CHANNEL_LAYERS", {}).values():
        for host in layer.get("CONFIG", {}).get("hosts", []):
            if isinstance(host, str):
                urls.append(host)
            elif isinstance(host, dict) and isinstance(host.get("address"), str):
                urls.append(host["address"])
    return urls


@register()
def check_channel_layer_redis_db(app_configs, **kwargs):
    others = {}

    broker = getattr(settings, "CELERY_BROKER_URL", None)
    if _redis_identity(broker):
        others[_redis_identity(broker)] = "CELERY_BROKER_URL"

    for alias, cache in getattr(settings, "CACHES", {}).items():
        locations = cache.get("LOCATION")
        for location in locations if isinstance(locations, (list, tuple)) else [locations]:
            if _redis_identity(location):
                others[_redis_identity(location)] = f"CACHES['{alias}']"

    warnings = []
    for url in _channel_layer_urls():
        identity = _redis_identity(url)
        if identity in others:
            warnings.append(
                Warning(
                    f"CHANNEL_LAYERS {others[identity]} bilan bir xil Redis DB'ni "
                    f"ishlatmoqda ({identity[0]}:{identity[1]}/{identity[2]}).",
                    hint="CHANNEL_LAYER_REDIS_URL uchun alohida, bo'sh Redis DB tanlang.",
                    id="notifications.W001",
                )
            )
    return warnings
