"""Settings de producción: endurecimiento por encima de `base`."""

from decouple import config

from .base import *  # noqa: F401,F403

DEBUG = False

SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
# El preload es irreversible una vez enviado a los navegadores: se activa
# conscientemente con `SECURE_HSTS_PRELOAD=True` cuando el dominio esté listo.
SECURE_HSTS_PRELOAD = config("SECURE_HSTS_PRELOAD", default=False, cast=bool)
X_FRAME_OPTIONS = "DENY"
