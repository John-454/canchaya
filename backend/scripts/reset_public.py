"""Resetea SOLO el esquema `public` de la BD de desarrollo (no borra `auth` de Supabase).

Uso: python scripts/reset_public.py --yes
Se niega a borrar si `usuarios` tiene filas.
"""

import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

import django  # noqa: E402

django.setup()

from django.db import connection  # noqa: E402

with connection.cursor() as c:
    if "--yes" not in sys.argv:
        raise SystemExit("Se requiere --yes para confirmar el borrado.")

    c.execute("SELECT to_regclass('public.usuarios')::text")
    if c.fetchone()[0]:
        c.execute("SELECT count(*) FROM public.usuarios")
        if c.fetchone()[0]:
            raise SystemExit("ABORTADO: usuarios tiene filas; no se destruye nada.")

    c.execute("""
        SELECT tablename FROM pg_tables
        WHERE schemaname = 'public' AND tablename NOT LIKE 'pg_%'
        """)
    tablas = [r[0] for r in c.fetchall()]

    # Las tablas propias de Django se borran con DROP TABLE; las de Supabase Auth
    # viven en el esquema `auth`, así que aquí solo aparecen las nuestras.
    for t in tablas:
        if t.startswith(("schema_migrations", "ar_internal_metadata")):
            continue
        c.execute(f'DROP TABLE IF EXISTS public."{t}" CASCADE')
        print("drop", t)

    c.execute("SELECT to_regprocedure('public.canchaya_timerange(time,time)')::text")
    if c.fetchone()[0]:
        c.execute("DROP FUNCTION public.canchaya_timerange(TIME, TIME)")
        print("drop function canchaya_timerange")
