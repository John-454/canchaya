"""Serializers del módulo fields (§5.2 — T3.4 a T3.8)."""

from __future__ import annotations

from decimal import Decimal

from rest_framework import serializers
from shared.exceptions import BLOQUE_NO_ALINEADO, BusinessRuleViolation

from modules.fields.models import Cancha, HorarioOperacion, ImagenCancha, Tarifa


def _validar_hora_en_punto(valor, campo: str):
    """R4: horas exactas en punto (minuto y segundo 0)."""
    if valor.minute != 0 or valor.second != 0:
        raise serializers.ValidationError(
            f"{campo} debe estar en punto (HH:00).", code=BLOQUE_NO_ALINEADO
        )
    return valor


def _validar_orden(inicio, fin, campo_inicio="hora_inicio", campo_fin="hora_fin"):
    if inicio is not None and fin is not None and fin <= inicio:
        raise serializers.ValidationError(
            {campo_fin: f"{campo_fin} debe ser posterior a {campo_inicio}."}
        )


class CanchaSerializer(serializers.ModelSerializer):
    """`GET / PATCH /api/v1/admin/field/` (Mi cancha)."""

    class Meta:
        model = Cancha
        fields = (
            "id_cancha",
            "nombre",
            "direccion",
            "zona",
            "descripcion",
            "precio_base",
            "estado",
            "fecha_creacion",
        )
        read_only_fields = ("id_cancha", "fecha_creacion")

    def validate_nombre(self, valor):
        if not (valor or "").strip():
            raise serializers.ValidationError("El nombre no puede estar vacío.")
        return valor.strip()

    def validate_precio_base(self, valor):
        if Decimal(valor) < 0:
            raise serializers.ValidationError("El precio base no puede ser negativo.")
        return valor


class ImagenSerializer(serializers.ModelSerializer):
    """Listado y registro de fotografías (T3.5)."""

    class Meta:
        model = ImagenCancha
        fields = ("id_imagen", "url_imagen", "descripcion", "imagen_principal", "fecha_creacion")
        read_only_fields = ("id_imagen", "fecha_creacion")

    def validate_url_imagen(self, valor):
        if not str(valor).startswith(("http://", "https://")):
            raise serializers.ValidationError("La URL debe empezar por http:// o https://")
        return valor


class ImagenUpdateSerializer(serializers.ModelSerializer):
    """`PATCH /images/{id}/`: solo descripción y marca de principal."""

    class Meta:
        model = ImagenCancha
        fields = ("descripcion", "imagen_principal")


class HorarioSerializer(serializers.ModelSerializer):
    """Franjas semanales de atención (T3.6)."""

    class Meta:
        model = HorarioOperacion
        fields = ("id_horario", "dia_semana", "hora_apertura", "hora_cierre", "activo")
        read_only_fields = ("id_horario",)

    def validate_dia_semana(self, valor):
        if not 1 <= valor <= 7:
            raise serializers.ValidationError(
                "dia_semana debe estar entre 1 (lunes) y 7 (domingo)."
            )
        return valor

    def validate_hora_apertura(self, valor):
        return _validar_hora_en_punto(valor, "hora_apertura")

    def validate_hora_cierre(self, valor):
        return _validar_hora_en_punto(valor, "hora_cierre")

    def validate(self, attrs):
        inicio = attrs.get("hora_apertura", getattr(self.instance, "hora_apertura", None))
        fin = attrs.get("hora_cierre", getattr(self.instance, "hora_cierre", None))
        _validar_orden(inicio, fin, "hora_apertura", "hora_cierre")
        return attrs


class TarifaSerializer(serializers.ModelSerializer):
    """Tarifas semanales y por fecha especial (T3.7)."""

    origen = serializers.SerializerMethodField()

    class Meta:
        model = Tarifa
        fields = (
            "id_tarifa",
            "dia_semana",
            "fecha_especial",
            "hora_inicio",
            "hora_fin",
            "precio_hora",
            "activo",
            "origen",
        )
        read_only_fields = ("id_tarifa", "origen")

    def get_origen(self, obj) -> str:
        return "especial" if obj.es_especial else "semanal"

    def validate_dia_semana(self, valor):
        if valor is not None and not 1 <= valor <= 7:
            raise serializers.ValidationError("dia_semana debe estar entre 1 y 7.")
        return valor

    def validate_hora_inicio(self, valor):
        return _validar_hora_en_punto(valor, "hora_inicio")

    def validate_hora_fin(self, valor):
        return _validar_hora_en_punto(valor, "hora_fin")

    def validate_precio_hora(self, valor):
        if Decimal(valor) <= 0:
            raise serializers.ValidationError("El precio por hora debe ser mayor que cero.")
        return valor

    def validate(self, attrs):
        instancia = self.instance
        dia = attrs.get("dia_semana", getattr(instancia, "dia_semana", None))
        fecha = attrs.get("fecha_especial", getattr(instancia, "fecha_especial", None))

        tiene_dia = dia is not None
        tiene_fecha = fecha is not None
        if tiene_dia == tiene_fecha:
            raise serializers.ValidationError(
                {
                    "dia_semana": "Indica exactamente uno: dia_semana (semanal) o "
                    "fecha_especial (fecha especial).",
                }
            )

        inicio = attrs.get("hora_inicio", getattr(instancia, "hora_inicio", None))
        fin = attrs.get("hora_fin", getattr(instancia, "hora_fin", None))
        _validar_orden(inicio, fin)
        return attrs


class PreviewQuerySerializer(serializers.Serializer):
    """Query string de `/rates/preview/?fecha=YYYY-MM-DD` (T3.8)."""

    fecha = serializers.DateField(required=True)


def error_de_negocio(exc: BusinessRuleViolation) -> serializers.ValidationError:
    return serializers.ValidationError({exc.code: exc.detail})
