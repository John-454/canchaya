"""Detalle de un esquema creado manualmente (para inspeccionar antes de migrar)."""

import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

import django  # noqa: E402

django.setup()

from django.db import connection  # noqa: E402

tablas = sys.argv[1:] or [
    "usuarios",
    "canchas",
    "imagenes_cancha",
    "horarios_operacion",
    "tarifas",
    "reservas",
]

with connection.cursor() as c:
    for t in tablas:
        print(f"\n{'=' * 70}\nTABLA {t}\n{'=' * 70}")
        c.execute(
            """
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema='public' AND table_name=%s
            ORDER BY ordinal_position
            """,
            [t],
        )
        for col, tipo, null, default in c.fetchall():
            print(f"  {col:22s} {tipo:20s} null={null:3s} default={default}")

        c.execute(
            """
            SELECT conname, con.contype, pg_get_constraintdef(con.oid)
            FROM pg_constraint con
            WHERE con.conrelid = ('public.' || %s)::regclass
            ORDER BY con.contype, conname
            """,
            [t],
        )
        print("  -- constraints --")
        for name, tipo, ddl in c.fetchall():
            print(f"  [{tipo}] {name}: {ddl}")

        c.execute(
            """
            SELECT indexname, indexdef FROM pg_indexes
            WHERE schemaname='public' AND tablename=%s ORDER BY indexname
            """,
            [t],
        )
        print("  -- indices --")
        for name, ddl in c.fetchall():
            print(f"  {name}: {ddl}")

    c.execute(
        "SELECT proname, pg_get_functiondef(oid) FROM pg_proc "
        "WHERE pronamespace = 'public'::regnamespace"
    )
    print("\nFUNCIONES EN public:")
    for name, ddl in c.fetchall():
        print(f"\n-- {name} --\n{ddl}")

    c.execute(
        "SELECT extname FROM pg_extension WHERE extname IN ('btree_gist','pgcrypto','uuid-ossp',"
        "'citext','pg_cron','pg_net')"
    )
    print("extensiones:", [r[0] for r in c.fetchall()])
