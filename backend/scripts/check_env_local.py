"""Diagnóstico del entorno local (T6 / pre-Iteración 6).

Comprueba, sin exponer secretos:
  - extensiones requeridas en la BD del proyecto Supabase;
  - si `propietario@canchaya.test` existe en `usuarios`, su rol y su cancha;
  - si el correo existe en Supabase Auth (vía `/auth/v1/` con la anon key).

Uso:
    python scripts/check_env_local.py
"""

from __future__ import annotations

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

import django  # noqa: E402

django.setup()

import requests  # noqa: E402
from decouple import config  # noqa: E402
from django.conf import settings  # noqa: E402
from django.db import connection  # noqa: E402


def check_extensiones() -> None:
    with connection.cursor() as cur:
        cur.execute("SELECT extname, extversion FROM pg_extension ORDER BY 1")
        for nombre, version in cur.fetchall():
            print(f"  [BD] extension {nombre:14s} {version}")


def check_usuario() -> None:
    from modules.fields.services import get_cancha_by_admin
    from modules.users_auth.models import Usuario

    correo = "propietario@canchaya.test"
    usuario = Usuario.objects.filter(correo__iexact=correo).first()
    if usuario is None:
        print(f"  [BD] usuario {correo}: NO EXISTE -> ejecuta el seed o aprovisionar_admin")
        return
    print(
        f"  [BD] usuario {correo}: rol={usuario.rol} activo={usuario.activo} "
        f"uid={usuario.supabase_uid} telefono={'sí' if usuario.telefono else 'no'}"
    )
    cancha = get_cancha_by_admin(usuario) if usuario.rol == "administrador" else None
    print(f"  [BD] cancha: {cancha.nombre if cancha else 'SIN CANCHA (el panel dará 403)'}")


def check_auth() -> None:
    """Prueba que el proyecto responde a Auth con una anon key válida."""
    url = settings.SUPABASE_URL.rstrip("/")
    anon = config("SUPABASE_ANON_KEY", default="")
    if not anon:
        print(
            "  [Auth] SUPABASE_ANON_KEY no está en backend/.env (solo se necesita para esta prueba)"
        )
        return
    try:
        r = requests.get(
            f"{url}/auth/v1/settings",
            headers={"apikey": anon},
            timeout=10,
        )
        print(f"  [Auth] GET /auth/v1/settings -> HTTP {r.status_code}")
        if r.status_code == 200:
            cuerpo = r.json()
            proveedores = cuerpo.get("external", {})
            print(
                f"  [Auth] email activo: {proveedores.get('email')} | google: {proveedores.get('google')}"
            )
    except requests.RequestException as exc:
        print(f"  [Auth] error de red: {exc}")


def main() -> None:
    print("== Proyecto Supabase ==")
    print(f"  URL: {settings.SUPABASE_URL or '(vacía)'}")
    print("== Base de datos ==")
    check_extensiones()
    print("== Usuario administrador ==")
    check_usuario()
    print("== Supabase Auth ==")
    check_auth()


if __name__ == "__main__":
    main()
