"""Simula el flujo del panel contra el servidor Django local (sin navegador).

Uso (con `manage.py runserver` corriendo en otra terminal):
    python scripts/smoke_auth.py
"""

from __future__ import annotations

import json
import os
import uuid

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

import django  # noqa: E402

django.setup()

import jwt  # noqa: E402
import requests  # noqa: E402
from decouple import config  # noqa: E402

BASE = "http://127.0.0.1:8000/api/v1"
SECRETO = config("SUPABASE_JWT_SECRET", default="")
URL = config("SUPABASE_URL", default="").rstrip("/")
ISSUER = f"{URL}/auth/v1"


def _token(rol_correo: str, uid: uuid.UUID, *, expira_en: int = 3600) -> str:
    import time

    ahora = int(time.time())
    payload = {
        "sub": str(uid),
        "aud": "authenticated",
        "iat": ahora,
        "exp": ahora + expira_en,
        "email": rol_correo,
        "iss": ISSUER,
        "user_metadata": {"email": rol_correo, "full_name": "Smoke Test"},
    }
    return jwt.encode(payload, SECRETO, algorithm="HS256")


def llamar(metodo: str, ruta: str, token: str | None = None):
    cabeceras = {"Authorization": f"Bearer {token}"} if token else {}
    r = requests.request(metodo, f"{BASE}{ruta}", headers=cabeceras, timeout=15)
    cuerpo = r.text[:180]
    print(f"  {metodo:5s} {ruta:34s} -> {r.status_code}  {cuerpo}")
    return r


def main() -> None:
    print("== 1. Sin token (debe ser 401 con WWW-Authenticate) ==")
    r = requests.get(f"{BASE}/admin/field/", timeout=15)
    print(
        f"  GET  /admin/field/                -> {r.status_code}  "
        f"WWW-Authenticate={r.headers.get('WWW-Authenticate')}"
    )

    print("== 2. Token inválido (firma incorrecta) -> 401 token_invalido ==")
    malo = jwt.encode(
        {"sub": str(uuid.uuid4()), "aud": "authenticated", "exp": 9999999999},
        "firma-que-no-es",
        algorithm="HS256",
    )
    llamar("GET", "/admin/field/", malo)

    print("== 3. Token expirado -> 401 token_expirado ==")
    llamar("GET", "/admin/field/", _token("x@canchaya.test", uuid.uuid4(), expira_en=-60))

    print("== 4. Token válido de perfil inexistente -> 401 perfil_no_sincronizado ==")
    uid_desconocido = uuid.uuid4()
    llamar(
        "GET", "/admin/field/", _token(f"nuevo-{uid_desconocido}@canchaya.test", uid_desconocido)
    )

    print("== 5. /auth/sync/ crea el perfil como cliente ==")
    t_nuevo = _token(f"cliente-{uid_desconocido}@canchaya.test", uid_desconocido)
    llamar("POST", "/auth/sync/", t_nuevo)

    print("== 6. Cliente en el panel -> 403 rol_requerido ==")
    llamar("GET", "/admin/field/", t_nuevo)

    print("== 7. Cliente intentando escalar rol -> 400 campo_no_permitido ==")
    r = requests.patch(
        f"{BASE}/auth/me/",
        json={"rol": "administrador"},
        headers={"Authorization": f"Bearer {t_nuevo}"},
        timeout=15,
    )
    print(f"  PATCH /auth/me/ {{rol}}           -> {r.status_code}  {r.text[:180]}")

    print("== 8. Admin aprovisionado (seed) -> 200 ==")
    from modules.users_auth.models import Usuario  # noqa: PLC0415

    admin = Usuario.objects.filter(correo__iexact="propietario@canchaya.test").first()
    if admin is None:
        print("  (sin admin en BD)")
        return
    t_admin = _token(admin.correo, admin.supabase_uid)
    llamar("POST", "/auth/sync/", t_admin)
    llamar("GET", "/admin/field/", t_admin)
    llamar("GET", "/admin/finance/dashboard/", t_admin)
    llamar("GET", "/admin/field/rates/preview/?fecha=2026-12-01", t_admin)
    print(json.dumps({"fin": "ok"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
