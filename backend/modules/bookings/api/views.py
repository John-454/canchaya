"""Vistas del módulo bookings (§5.3 — T4.4 a T4.6).

Todas heredan de `MiCanchaAPIView` (permiso `IsFieldAdmin`) y, al inicio de cada
consulta, ejecutan la transición automática a `Finalizada` (R7) para que el
panel nunca muestre reservas vencidas como activas.
"""

from __future__ import annotations

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from shared.pagination import DefaultPagination
from shared.permissions import IsFieldAdmin

from modules.bookings import services
from modules.bookings.api.serializers import (
    CancelarSerializer,
    ReservaFiltroSerializer,
    ReservaSerializer,
)


class AdminBookingsAPIView(APIView):
    permission_classes = [IsFieldAdmin]

    @property
    def cancha(self):
        return self.request.cancha

    def despues_de_expirar(self):
        services.expire_confirmed_bookings(self.cancha)


class BookingListCreateView(AdminBookingsAPIView):
    """GET /api/v1/admin/bookings/ — filtrable y paginado (T4.4)."""

    def get(self, request):
        self.despues_de_expirar()
        filtros = ReservaFiltroSerializer(data=request.query_params)
        filtros.is_valid(raise_exception=True)
        qs = services.list_admin_bookings(self.cancha, filtros.validated_data)

        paginador = DefaultPagination()
        pagina = paginador.paginate_queryset(qs, request, view=self)
        datos = ReservaSerializer(pagina, many=True).data
        return paginador.get_paginated_response(datos)


class BookingDetailView(AdminBookingsAPIView):
    """GET /api/v1/admin/bookings/{id_reserva}/ (T4.5)."""

    def get(self, request, id_reserva: int):
        self.despues_de_expirar()
        reserva = services.get_admin_booking(self.cancha, id_reserva)
        return Response(ReservaSerializer(reserva).data)


class BookingApproveView(AdminBookingsAPIView):
    """POST .../approve/ — Pendiente → Confirmada (T4.6)."""

    def post(self, request, id_reserva: int):
        reserva = services.approve(self.cancha, id_reserva)
        return Response(ReservaSerializer(reserva).data)


class BookingCancelView(AdminBookingsAPIView):
    """POST .../cancel/ — Pendiente|Confirmada → Cancelada."""

    def post(self, request, id_reserva: int):
        body = CancelarSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        reserva = services.cancel(self.cancha, id_reserva, body.validated_data.get("motivo"))
        return Response(ReservaSerializer(reserva).data)


class BookingMarkPaidView(AdminBookingsAPIView):
    """POST .../mark-paid/ — estado_pago → Pagado + fecha_pago = now."""

    def post(self, request, id_reserva: int):
        reserva = services.mark_paid(self.cancha, id_reserva)
        return Response(ReservaSerializer(reserva).data)


__all__ = [
    "BookingListCreateView",
    "BookingDetailView",
    "BookingApproveView",
    "BookingCancelView",
    "BookingMarkPaidView",
    "status",
]
