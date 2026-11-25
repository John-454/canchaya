"""Crea y elimina la base de datos de test en Supabase.

`pytest-django` usa `test_<DB>` (aquí `test_postgres`). Con el Session pooler
las conexiones pueden quedar colgadas y dejar la base "en uso".
"""

import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

import django  # noqa: E402

django.setup()

from django.db import connection  # noqa: E402

TEST_DB = "test_postgres"


def drop() -> None:
    connection.close()
    autocommit = connection.autocommit
    connection.autocommit = True
    with connection.cursor() as c:
        c.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE datname = %s AND pid <> pg_backend_pid()",
            [TEST_DB],
        )
        c.execute(f'DROP DATABASE IF EXISTS "{TEST_DB}" WITH (FORCE)')
    connection.autocommit = autocommit
    print(f"base {TEST_DB} eliminada")


def status() -> None:
    with connection.cursor() as c:
        c.execute("SELECT count(*) FROM pg_database WHERE datname = %s", [TEST_DB])
        print(f"{TEST_DB} existe:", c.fetchone()[0] == 1)
        c.execute("SELECT count(*) FROM pg_stat_activity WHERE datname = %s", [TEST_DB])
        print("sesiones abiertas:", c.fetchone()[0])


if __name__ == "__main__":
    accion = sys.argv[1] if len(sys.argv) > 1 else "status"
    if accion == "drop":
        drop()
    else:
        status()
