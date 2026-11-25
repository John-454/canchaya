"""URLs del panel de administrador del módulo fields (§5.2).

Todas las vistas heredan de `MiCanchaAPIView` (permiso `IsFieldAdmin`): el
administrador solo puede operar sobre su propia cancha (1:1).
"""

from django.urls import path

from modules.fields.api.views import (
    HorarioDetailView,
    HorarioListCreateView,
    ImagenDetailView,
    ImagenListCreateView,
    MiCanchaView,
    PrecioRangoView,
    TarifaDetailView,
    TarifaListCreateView,
    TarifasPreviewView,
)

urlpatterns = [
    path("", MiCanchaView.as_view(), name="admin-field"),
    path("images/", ImagenListCreateView.as_view(), name="admin-field-images"),
    path(
        "images/<int:id_imagen>/",
        ImagenDetailView.as_view(),
        name="admin-field-image-detail",
    ),
    path("schedules/", HorarioListCreateView.as_view(), name="admin-field-schedules"),
    path(
        "schedules/<int:id_horario>/",
        HorarioDetailView.as_view(),
        name="admin-field-schedule-detail",
    ),
    path("rates/", TarifaListCreateView.as_view(), name="admin-field-rates"),
    # Debe ir antes del detalle por id numérico.
    path("rates/preview/", TarifasPreviewView.as_view(), name="admin-field-rates-preview"),
    path("rates/quote/", PrecioRangoView.as_view(), name="admin-field-rates-quote"),
    path(
        "rates/<int:id_tarifa>/",
        TarifaDetailView.as_view(),
        name="admin-field-rate-detail",
    ),
]
