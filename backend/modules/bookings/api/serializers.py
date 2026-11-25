"""Serializers del módulo bookings (§5.3)."""

from __future__ import annotations

from rest_framework import serializers

from modules.bookings.models import EstadoPago, EstadoReserva, Reserva


class ReservaSerializer(serializers.ModelSerializer):
    """Listado y detalle del panel (T4.4 / T4.5)."""

    cliente = serializers.SerializerMethodField()

    class Meta:
        model = Reserva
        fields = (
            "id_reserva",
            "codigo_reserva",
            "fecha_reserva",
            "hora_inicio",
            "hora_fin",
            "precio_total",
            "estado_reserva",
            "estado_pago",
            "fecha_pago",
            "observaciones",
            "fecha_creacion",
            "cliente",
        )
        read_only_fields = fields

    def get_cliente(self, obj) -> dict:
        return {
            "id_cliente": obj.id_cliente_id,
            "nombre": obj.nombre_cliente,
            "correo": obj.correo_cliente,
            "telefono": obj.telefono_cliente,
        }


class ReservaFiltroSerializer(serializers.Serializer):
    fecha = serializers.DateField(required=False)
    estado_reserva = serializers.ChoiceField(choices=EstadoReserva.choices, required=False)
    estado_pago = serializers.ChoiceField(choices=EstadoPago.choices, required=False)
    cliente = serializers.CharField(required=False, max_length=150)
    codigo_reserva = serializers.CharField(required=False, max_length=30)


class CancelarSerializer(serializers.Serializer):
    motivo = serializers.CharField(required=False, allow_blank=True, max_length=250)
