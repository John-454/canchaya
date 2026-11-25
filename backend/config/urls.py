"""URLs raíz: monta la API v1 de cada módulo de dominio."""

from django.urls import include, path
from shared.health import health
from shared.openapi import schema_view

urlpatterns = [
    path("api/v1/health/", health, name="health"),
    path("api/v1/schema/", schema_view, name="schema"),
    # FASE 1 — disponibles
    path("api/v1/auth/", include("modules.users_auth.api.urls")),
    path("api/v1/admin/field/", include("modules.fields.api.urls")),
    path("api/v1/admin/bookings/", include("modules.bookings.api.urls")),
    path("api/v1/admin/finance/", include("modules.finance.api.urls")),
]
