"""
Configuración común de canchaya. (Monolito Modular).

Frontera entre módulos: ningún módulo importa `models` de otro módulo.
La comunicación se hace a través de `shared/` y de `services.py` de cada módulo.
"""

import re
from pathlib import Path
from urllib.parse import unquote, urlparse

from decouple import Csv, config

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def _postgres_from_url(url: str) -> dict:
    """Convierte una URI `postgresql://...` en los parámetros de Django.

    Soporta el formato de Supabase (Session pooler):
    `postgresql://postgres.<ref>:<pw>@aws-0-<region>.pooler.supabase.com:5432/postgres`
    Las credenciales de la URI tienen prioridad sobre las variables sueltas.
    Tolera corchetes alrededor del host (`@[host]:5432`), que algunos
    dashboards muestran como marcador de plantilla.
    """
    url = url.strip().strip('"').strip("'")
    if not any(c.isdigit() for c in url):
        raise ValueError(
            "DATABASE_URL parece una plantilla: reemplaza <ref>, <password>, <region>."
        )
    url = re.sub(r"@\[([^\]]+)\]", r"@\1", url)
    url = url.replace("[", "").replace("]", "")
    parsed = urlparse(url)
    if parsed.scheme not in {"postgres", "postgresql"}:
        raise ValueError("DATABASE_URL debe empezar por postgresql:// o postgres://")
    return {
        "NAME": (parsed.path or "/postgres").lstrip("/"),
        "USER": unquote(parsed.username or ""),
        "PASSWORD": unquote(parsed.password or ""),
        "HOST": parsed.hostname or "",
        "PORT": str(parsed.port or 5432),
    }


DATABASE_URL = config("DATABASE_URL", default="")

SECRET_KEY = config("DJANGO_SECRET_KEY", default="dev-insecure-key")
DEBUG = config("DJANGO_DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config("DJANGO_ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())

# ---------------------------------------------------------------------------
# Apps
# ---------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "django_filters",
    "corsheaders",
]

# Monolito modular: un Django "app" por dominio de negocio.
LOCAL_APPS = [
    "modules.users_auth",
    "modules.fields",
    "modules.bookings",
    "modules.finance",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ---------------------------------------------------------------------------
# Base de datos (PostgreSQL + btree_gist para exclusion constraints)
# ---------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("POSTGRES_DB", default="canchaya"),
        "USER": config("POSTGRES_USER", default="canchaya"),
        "PASSWORD": config("POSTGRES_PASSWORD", default="canchaya"),
        "HOST": config("POSTGRES_HOST", default="127.0.0.1"),
        "PORT": config("POSTGRES_PORT", default="5432"),
        "ATOMIC_REQUESTS": True,
        "CONN_MAX_AGE": 60,
        "OPTIONS": {"connect_timeout": 15, "sslmode": "require"},
    }
}

# Prioridad: DATABASE_URL (URI de Supabase) > variables POSTGRES_*.
if DATABASE_URL:
    DATABASES["default"].update(_postgres_from_url(DATABASE_URL))
# Sin DATABASE_URL y sin POSTGRES_HOST explícito -> Postgres local.
elif not config("POSTGRES_HOST", default=""):
    DATABASES["default"]["OPTIONS"]["sslmode"] = "prefer"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Auth: el modelo de usuario es el del módulo users_auth (no Django auth)
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = "users_auth.Usuario"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# i18n / TZ — la hora del servidor de negocio es Colombia
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "es-co"
TIME_ZONE = config("DJANGO_TIME_ZONE", default="America/Bogota")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_ROOT = BASE_DIR / "media"

# ---------------------------------------------------------------------------
# DRF
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "shared.auth.authentication.SupabaseJWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    # No se usa `UNAUTHENTICATED_USER = None`: DRF necesita un request.user
    # anónimo para que `get_authenticate_header()` decida entre 401 y 403.
    "DEFAULT_PAGINATION_CLASS": "shared.pagination.DefaultPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.OrderingFilter",
    ],
    "EXCEPTION_HANDLER": "shared.exceptions_handler.custom_exception_handler",
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    # Endurecimiento (T6.1): límites por IP. `/auth/sync/` es el endpoint más
    # expuesto porque acepta tokens de cualquier usuario nuevo.
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/min",
        "user": "300/min",
        "auth_sync": "20/min",
    },
}

# ---------------------------------------------------------------------------
# Supabase
# ---------------------------------------------------------------------------
SUPABASE_URL = config("SUPABASE_URL", default="")
SUPABASE_JWT_SECRET = config("SUPABASE_JWT_SECRET", default="")
SUPABASE_JWKS_CACHE_TTL = config("SUPABASE_JWKS_CACHE_TTL", default=3600, cast=int)

# ---------------------------------------------------------------------------
# CORS y CSRF (T6.2)
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = config("CORS_ALLOWED_ORIGINS", default="http://localhost:5173", cast=Csv())
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    "accept",
    "authorization",
    "content-type",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]

# La API es stateless (JWT de Supabase); se declaran los orígenes de confianza
# por si alguna vista usa cookies.
CSRF_TRUSTED_ORIGINS = config("CSRF_TRUSTED_ORIGINS", default="http://localhost:5173", cast=Csv())

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
DATA_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024  # 2 MB

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "{levelname} {asctime} {name} {message}", "style": "{"},
        "json": {"format": "{message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    # T6.3: errores 4xx/5xx con su traza, sin datos sensibles.
    "loggers": {
        "django.request": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "modules.bookings": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
