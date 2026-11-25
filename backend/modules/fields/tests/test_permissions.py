"""Aislamiento 1:1 del permiso `IsFieldAdmin` (T2.6)."""

from __future__ import annotations

import uuid

import pytest
from django.contrib.auth.models import AnonymousUser
from rest_framework.test import APIRequestFactory
from shared.permissions import IsFieldAdmin

from modules.fields.models import Cancha
from modules.users_auth.models import Rol, Usuario


def _request(usuario):
    request = APIRequestFactory().get("/x/")
    request.user = usuario
    return request


def _otro_admin(idx: int) -> tuple[Usuario, Cancha]:
    admin = Usuario.objects.create(
        supabase_uid=uuid.uuid4(),
        nombre=f"Admin {idx}",
        correo=f"admin{idx}@canchaya.test",
        rol=Rol.ADMINISTRADOR,
    )
    cancha = Cancha.objects.create(
        id_administrador=admin, nombre=f"Cancha {idx}", direccion=f"Calle {idx}"
    )
    return admin, cancha


@pytest.mark.django_db
def test_cada_admin_obtiene_su_propia_cancha(admin_user, cancha):
    otro_admin, otra_cancha = _otro_admin(2)

    request_a = _request(admin_user)
    assert IsFieldAdmin().has_permission(request_a, None) is True
    assert request_a.cancha.pk == cancha.pk
    assert request_a.cancha.pk != otra_cancha.pk

    request_b = _request(otro_admin)
    assert IsFieldAdmin().has_permission(request_b, None) is True
    assert request_b.cancha.pk == otra_cancha.pk


@pytest.mark.django_db
def test_admin_sin_cancha_marcado_en_request():
    from shared.exceptions import ADMIN_SIN_CANCHA, ForbiddenError

    admin = Usuario.objects.create(
        supabase_uid=uuid.uuid4(),
        nombre="Sin Cancha",
        correo="sin-cancha@canchaya.test",
        rol=Rol.ADMINISTRADOR,
    )
    with pytest.raises(ForbiddenError) as exc:
        IsFieldAdmin().has_permission(_request(admin), None)
    assert exc.value.code == ADMIN_SIN_CANCHA


@pytest.mark.django_db
def test_cliente_y_anonimo_rechazados(cliente):
    from shared.exceptions import ROL_REQUERIDO, ForbiddenError

    with pytest.raises(ForbiddenError) as exc:
        IsFieldAdmin().has_permission(_request(cliente), None)
    assert exc.value.code == ROL_REQUERIDO

    # Anónimo: devuelve False para que DRF emita el 401 (con WWW-Authenticate).
    assert IsFieldAdmin().has_permission(_request(AnonymousUser()), None) is False


@pytest.mark.django_db
def test_pertenencia_1_1_no_es_lista(admin_user, cancha):
    """Un admin nunca recibe una colección: la cancha es un único objeto."""
    _otro_admin(3)
    request = _request(admin_user)
    IsFieldAdmin().has_permission(request, None)
    assert isinstance(request.cancha, Cancha)
    assert Cancha.objects.filter(id_administrador=admin_user).count() == 1
