"""Servicios públicos del módulo `users_auth` (T2.7).

Otros módulos **no** importan `modules.users_auth.models`: usan estas funciones.
"""

from __future__ import annotations

import re
import uuid

from django.db import transaction
from django.db.models import Q
from shared.auth.supabase import ClaimsToken
from shared.exceptions import TELEFONO_REQUERIDO, BusinessRuleViolation, ConflictError

from modules.users_auth.models import Rol, Usuario

_TELEFONO_CO = re.compile(r"^(?:\+?57)?(\d{10})$")


# ---------------------------------------------------------------------------
# Lectura
# ---------------------------------------------------------------------------
def get_usuario(usuario_id: int) -> Usuario | None:
    return Usuario.objects.filter(pk=usuario_id).first()


def get_usuario_por_uid(supabase_uid: uuid.UUID | str) -> Usuario | None:
    return Usuario.objects.filter(supabase_uid=supabase_uid).first()


def get_usuario_por_correo(correo: str) -> Usuario | None:
    return Usuario.objects.filter(correo__iexact=(correo or "").strip()).first()


def resolver_usuario_autenticado(claims: ClaimsToken) -> Usuario | None:
    """Busca el perfil por `supabase_uid`; si no existe y el correo coincide con
    un perfil aprovisionado (Opción A), vincula el `sub` del token a ese perfil.
    """
    usuario = get_usuario_por_uid(claims.sub)
    if usuario is not None:
        return usuario
    if not claims.correo:
        return None

    usuario = get_usuario_por_correo(claims.correo)
    if usuario is None:
        return None

    uid = uuid.UUID(str(claims.sub))
    if Usuario.objects.filter(supabase_uid=uid).exclude(pk=usuario.pk).exists():
        return None
    usuario.supabase_uid = uid
    usuario.save(update_fields=["supabase_uid"])
    return usuario


# ---------------------------------------------------------------------------
# Escritura
# ---------------------------------------------------------------------------
def normalizar_telefono(telefono: str) -> str:
    """Valida y normaliza un teléfono colombiano a `+57XXXXXXXXXX`."""
    valor = (telefono or "").strip().replace(" ", "").replace("-", "")
    coincide = _TELEFONO_CO.match(valor)
    if not coincide:
        raise BusinessRuleViolation(
            "El teléfono debe tener 10 dígitos (celular colombiano), con o sin +57.",
            code="telefono_invalido",
            errors={"telefono": telefono},
        )
    digitos = coincide.group(1)
    if not digitos.startswith("3"):
        raise BusinessRuleViolation(
            "El teléfono debe ser un celular colombiano (empezar por 3).",
            code="telefono_invalido",
            errors={"telefono": telefono},
        )
    return f"+57{digitos}"


def require_telefono(usuario: Usuario) -> str:
    """R1: obligatorio antes de confirmar cualquier reserva."""
    if usuario.requiere_telefono:
        raise BusinessRuleViolation(
            "Debes registrar tu teléfono antes de confirmar una reserva.",
            code=TELEFONO_REQUERIDO,
            errors={"telefono": "requerido"},
        )
    return usuario.telefono


@transaction.atomic
def sync_usuario(claims: ClaimsToken) -> tuple[Usuario, bool]:
    """Crea o actualiza el perfil tras validar el token (T2.3).

    - Rol por defecto: `cliente` (nunca se sobrescribe un rol existente).
    - Idempotente: dos llamadas seguidas no duplican ni cambian nada.
    - Devuelve `(usuario, creado)`.
    """
    if not claims.correo:
        raise BusinessRuleViolation(
            "El token no incluye un correo válido.", code="correo_requerido"
        )

    uid = uuid.UUID(str(claims.sub))
    usuario = Usuario.objects.select_for_update().filter(Q(supabase_uid=uid)).first()
    creado = False

    if usuario is None:
        # Perfil aprovisionado antes del primer login (solo administradores):
        # se vincula por correo y se conserva su rol.
        usuario = Usuario.objects.select_for_update().filter(correo__iexact=claims.correo).first()
        if usuario is not None:
            if Usuario.objects.filter(supabase_uid=uid).exclude(pk=usuario.pk).exists():
                raise ConflictError(
                    "El uid de Supabase ya está vinculado a otro perfil.",
                    code="uid_ya_vinculado",
                )
            usuario.supabase_uid = uid
            usuario.save(update_fields=["supabase_uid"])
        else:
            usuario = Usuario.objects.create(
                supabase_uid=uid,
                correo=claims.correo,
                nombre=claims.nombre or claims.correo.split("@")[0],
                rol=Rol.CLIENTE,
            )
            creado = True

    # Sincroniza solo datos que Supabase es dueño de la verdad.
    cambios: list[str] = []
    nombre = (claims.nombre or "").strip()
    if nombre and not usuario.rol == Rol.ADMINISTRADOR and nombre != usuario.nombre:
        usuario.nombre = nombre[:120]
        cambios.append("nombre")
    if cambios:
        usuario.save(update_fields=cambios)

    return usuario, creado


@transaction.atomic
def update_perfil(usuario: Usuario, datos: dict) -> Usuario:
    """`PATCH /auth/me/`: permite `nombre` y `telefono` (T2.5)."""
    campos_protegidos = {"rol", "activo", "supabase_uid", "correo", "id_usuario"}
    intentos = campos_protegidos.intersection(datos.keys())
    if intentos:
        raise BusinessRuleViolation(
            f"Campos no modificables: {', '.join(sorted(intentos))}.",
            code="campo_no_permitido",
            errors={campo: "no modificable" for campo in sorted(intentos)},
        )

    cambios: list[str] = []
    if "nombre" in datos:
        nombre = (datos["nombre"] or "").strip()
        if not nombre:
            raise BusinessRuleViolation(
                "El nombre no puede estar vacío.",
                code="datos_invalidos",
                errors={"nombre": "requerido"},
            )
        usuario.nombre = nombre[:120]
        cambios.append("nombre")

    if "telefono" in datos:
        telefono = datos["telefono"]
        usuario.telefono = normalizar_telefono(telefono) if telefono else None
        cambios.append("telefono")

    if cambios:
        usuario.save(update_fields=cambios)
    return usuario


@transaction.atomic
def aprovisionar_admin(
    *,
    correo: str,
    supabase_uid: uuid.UUID | str | None = None,
    nombre: str | None = None,
    telefono: str | None = None,
) -> Usuario:
    """Alta controlada de un administrador (Opción A).

    Si el perfil ya existe por correo, se actualiza su rol y (si se conoce) el
    `supabase_uid`. Si no existe y hay `supabase_uid`, se crea.
    """
    correo = (correo or "").strip().lower()
    if not correo:
        raise BusinessRuleViolation("El correo es obligatorio.", code="correo_requerido")

    uid = uuid.UUID(str(supabase_uid)) if supabase_uid else None
    usuario = get_usuario_por_correo(correo)

    if uid is not None:
        existente = get_usuario_por_uid(uid)
        if existente is not None and (usuario is None or existente.pk != usuario.pk):
            raise ConflictError(
                f"El supabase_uid {uid} ya pertenece a {existente.correo}.",
                code="uid_ya_vinculado",
            )

    if usuario is None:
        if uid is None:
            raise BusinessRuleViolation(
                "Para crear un administrador nuevo el supabase_uid es obligatorio.",
                code="uid_requerido",
            )
        usuario = Usuario.objects.create(
            supabase_uid=uid,
            correo=correo,
            nombre=(nombre or correo.split("@")[0])[:120],
            telefono=normalizar_telefono(telefono) if telefono else None,
            rol=Rol.ADMINISTRADOR,
        )
        return usuario

    cambios: list[str] = ["rol"]
    usuario.rol = Rol.ADMINISTRADOR
    if uid is not None and usuario.supabase_uid != uid:
        usuario.supabase_uid = uid
        cambios.append("supabase_uid")
    if nombre:
        usuario.nombre = nombre[:120]
        cambios.append("nombre")
    if telefono:
        usuario.telefono = normalizar_telefono(telefono)
        cambios.append("telefono")
    usuario.save(update_fields=cambios)
    return usuario


__all__ = [
    "Usuario",
    "Rol",
    "get_usuario",
    "get_usuario_por_uid",
    "get_usuario_por_correo",
    "resolver_usuario_autenticado",
    "sync_usuario",
    "update_perfil",
    "require_telefono",
    "normalizar_telefono",
    "aprovisionar_admin",
]
