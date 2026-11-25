"""Inventario de lo que ya existe en `public` antes de migrar."""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

import django  # noqa: E402

django.setup()

from django.db import connection  # noqa: E402

TABLAS_NEGOCIO = (
    "usuarios",
    "canchas",
    "imagenes_cancha",
    "horarios_operacion",
    "tarifas",
    "reservas",
)

with connection.cursor() as c:
    c.execute("""
        SELECT table_name, table_type
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name
        """)
    print("OBJETOS EN public:")
    for name, tipo in c.fetchall():
        print(f"  - {name}  [{tipo}]")

    c.execute(
        "SELECT conname, conrelid::regclass::text FROM pg_constraint "
        "WHERE contype = 'x' AND connamespace = 'public'::regnamespace"
    )
    print("exclusiones existentes:", c.fetchall())

    c.execute("SELECT to_regclass('public.django_migrations')::text")
    print("django_migrations:", c.fetchone()[0])

    c.execute("SELECT to_regprocedure('public.canchaya_timerange(time,time)')::text")
    print("funcion canchaya_timerange:", c.fetchone()[0])

    print("TABLAS DEL MODELO:")
    for t in TABLAS_NEGOCIO:
        c.execute("SELECT to_regclass(%s)::text", [f"public.{t}"])
        reg = c.fetchone()[0]
        n = "-"
        if reg:
            c.execute(f"SELECT count(*) FROM public.{t}")
            n = c.fetchone()[0]
        print(f"  {t:20s} -> {reg or 'NO EXISTE':18s} filas={n}")
