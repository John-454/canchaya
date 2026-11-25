"""Vistas del módulo finance (§5.4 — T4.10 / T4.11)."""

from __future__ import annotations

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from shared.permissions import IsFieldAdmin

from modules.bookings.services import expire_confirmed_bookings
from modules.finance import selectors


class AdminFinanceAPIView(APIView):
    permission_classes = [IsFieldAdmin]

    @property
    def cancha(self):
        return self.request.cancha

    def despues_de_expirar(self):
        expire_confirmed_bookings(self.cancha)


class DashboardView(AdminFinanceAPIView):
    """GET /api/v1/admin/finance/dashboard/ (T4.10)."""

    def get(self, request):
        self.despues_de_expirar()
        return Response(
            {
                "kpis": selectors.kpis_dashboard(self.cancha),
                "serie_actividad": selectors.serie_actividad(self.cancha),
                "serie_ingresos": selectors.serie_ingresos(self.cancha),
                "solicitudes_por_aprobar": selectors.solicitudes_por_aprobar(self.cancha),
                "proximos_partidos": selectors.proximos_partidos(self.cancha),
            }
        )


class SummaryView(AdminFinanceAPIView):
    """GET /api/v1/admin/finance/summary/?period=day|week|month|custom (T4.11)."""

    def get(self, request):
        self.despues_de_expirar()
        period = request.query_params.get("period", "day")
        rango = selectors.resolver_rango(
            period, request.query_params.get("start"), request.query_params.get("end")
        )
        return Response(selectors.summary(self.cancha, rango))


__all__ = ["DashboardView", "SummaryView", "status"]
