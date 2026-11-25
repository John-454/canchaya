"""Diagnóstico de conexión y permisos (verificación Iteración 1)."""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402
from django.db import connection  # noqa: E402

d = settings.DATABASES["default"]
print(
    "HOST:",
    d["HOST"],
    "| PORT:",
    d["PORT"],
    "| NAME:",
    d["NAME"],
    "| SSL:",
    d["OPTIONS"].get("sslmode"),
)

with connection.cursor() as c:
    c.execute("select current_database(), current_user, version()")
    db, user, version = c.fetchone()
    print("CONEXION OK:", db, "/", user)
    print("VERSION:", version.split(",")[0])

    c.execute("select rolcreatedb from pg_roles where rolname = current_user")
    print("rol puede CREATE DATABASE:", c.fetchone())

    c.execute(
        "select extname, extversion from pg_extension "
        "where extname in ('btree_gist','pgcrypto','uuid-ossp','citext')"
    )
    print("extensiones ya instaladas:", c.fetchall())

    c.execute("select count(*) from information_schema.tables where table_schema='public'")
    print("tablas en public:", c.fetchone()[0])
