"""Serializers del módulo users_auth (§5.1)."""

from __future__ import annotations

from rest_framework import serializers

from modules.users_auth.models import Usuario


class UsuarioSerializer(serializers.ModelSerializer):
    """Perfil devuelto por `/auth/sync/` y `/auth/me/`."""

    requiere_telefono = serializers.BooleanField(read_only=True)

    class Meta:
        model = Usuario
        fields = (
            "id_usuario",
            "supabase_uid",
            "nombre",
            "correo",
            "telefono",
            "rol",
            "activo",
            "requiere_telefono",
            "fecha_creacion",
        )
        read_only_fields = fields


class PerfilUpdateSerializer(serializers.Serializer):
    """`PATCH /auth/me/`: solo nombre y teléfono (T2.5).

    Los campos protegidos se aceptan aquí solo para devolver un 400 explícito
    ('campo_no_permitido') en lugar de ignorarlos en silencio.
    """

    nombre = serializers.CharField(max_length=120, required=False)
    telefono = serializers.CharField(max_length=30, required=False, allow_blank=True)
    rol = serializers.CharField(required=False)
    activo = serializers.BooleanField(required=False)
    supabase_uid = serializers.CharField(required=False)
    correo = serializers.EmailField(required=False)
    id_usuario = serializers.IntegerField(required=False)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError({"detail": "Envía al menos 'nombre' o 'telefono'."})
        return attrs
