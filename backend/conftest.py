"""Configuración de pytest para el backend de canchaya.

La base de test (`test_postgres`) se crea desde cero, sin las extensiones de la
base principal. `btree_gist` es imprescindible para las `ExclusionConstraint`
de `fields`, así que se habilita en la base de test ANTES de que pytest-django
aplique las migraciones (por eso se hace en `pytest_configure` y no en un
fixture).
"""

from __future__ import annotations

import psycopg
from decouple import config

# Reexporta las fixtures de datos para que pytest las descubra.
from shared.tests.fixtures import *  # noqa: E402,F403
from shared.tests.tokens import (  # noqa: E402,F401
    claves_ec,
    claves_rsa,
    construir_token,
    supabase_es256,
    supabase_hs256,
    supabase_rs256,
    token_expirado,
)


def _test_conn_params() -> dict:
    from config.settings.base import _postgres_from_url  # noqa: PLC0415

    url = config("DATABASE_URL", default="")
    if url:
        params = _postgres_from_url(url)
    else:
        params = {
            "HOST": config("POSTGRES_HOST", default="127.0.0.1"),
            "PORT": config("POSTGRES_PORT", default="5432"),
            "USER": config("POSTGRES_USER", default="canchaya"),
            "PASSWORD": config("POSTGRES_PASSWORD", default="canchaya"),
            "NAME": config("POSTGRES_DB", default="canchaya"),
        }
    params["dbname"] = "test_" + params.pop("NAME")
    # psycopg usa nombres distintos a los de Django: user / password / host / port.
    params["user"] = params.pop("USER")
    params["password"] = params.pop("PASSWORD", "")
    params["host"] = params.pop("HOST", "127.0.0.1")
    params["port"] = int(params.pop("PORT", 5432))
    return params


def pytest_configure(config) -> None:
    """Prepara la base de test antes de que pytest-django la cree o migre.

    El Session pooler de Supabase deja sesiones colgadas y entonces la base
    `test_<DB>` no puede recrearse (`is being accessed by other users`). Por eso:
      1. si la base existe, se termina cualquier sesión y se elimina;
      2. la migración `users_auth.0001_enable_btree_gist` la recrea con la extensión.

    Si la base no se puede eliminar, se lanza un error claro en vez de un
    `SystemExit: 2` críptico de Django.
    """
    params = _test_conn_params()
    dbname = params["dbname"]
    try:
        admin = dict(params, dbname="postgres")
        with psycopg.connect(**admin, sslmode="require", connect_timeout=15) as conn:
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = %s AND pid <> pg_backend_pid()",
                    [dbname],
                )
                cur.execute(f'DROP DATABASE IF EXISTS "{dbname}" WITH (FORCE)')
    except Exception as exc:  # noqa: BLE001
        import pytest  # noqa: PLC0415

        pytest.exit(
            f"No se pudo limpiar la base de test '{dbname}': {exc}. "
            "Ejecuta `python scripts/test_db.py drop` y reintenta.",
            returncode=2,
        )
