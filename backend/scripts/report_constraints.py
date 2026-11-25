"""Reporte de verificación de constraints (Iteración 1)."""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

import django  # noqa: E402

django.setup()

from django.db import connection  # noqa: E402

TABLAS = ["usuarios", "canchas", "imagenes_cancha", "horarios_operacion", "tarifas", "reservas"]


def seccion(t):
    print(f"\n### {t}")


with connection.cursor() as c:
    c.execute("SELECT extname, extversion FROM pg_extension WHERE extname='btree_gist'")
    print("btree_gist:", c.fetchone())
    c.execute("SELECT canchaya_timerange('08:00'::time,'10:00'::time)::text")
    print("canchaya_timerange('08:00','10:00') =", c.fetchone()[0])

    print("\n## EXCLUSION CONSTRAINTS")
    c.execute("""
        SELECT conrelid::regclass::text AS tabla, conname, pg_get_constraintdef(oid)
        FROM pg_constraint
        WHERE contype = 'x' AND connamespace = 'public'::regnamespace
        ORDER BY tabla, conname
        """)
    rows = c.fetchall()
    for tabla, nombre, ddl in rows:
        print(f"\n[{tabla}] {nombre}\n  {ddl}")
    print(f"\nTOTAL exclusiones: {len(rows)}")

    print("\n## UNIQUE CONSTRAINTS / INDICES UNICOS PARCIALES")
    for t in TABLAS:
        c.execute(
            "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint "
            "WHERE conrelid=('public.'||%s)::regclass AND contype='u' ORDER BY conname",
            [t],
        )
        for nombre, ddl in c.fetchall():
            print(f"[{t}] {nombre}: {ddl}")
        c.execute(
            "SELECT indexname, indexdef FROM pg_indexes WHERE schemaname='public' "
            "AND tablename=%s AND indexdef LIKE '%%UNIQUE%%' AND indexdef LIKE '%%WHERE%%'",
            [t],
        )
        for nombre, ddl in c.fetchall():
            print(f"[{t}] (indice parcial) {nombre}: {ddl}")

    print("\n## CHECK CONSTRAINTS")
    for t in TABLAS:
        c.execute(
            "SELECT conname FROM pg_constraint WHERE conrelid=('public.'||%s)::regclass "
            "AND contype='c' ORDER BY conname",
            [t],
        )
        nombres = [r[0] for r in c.fetchall()]
        print(f"[{t}] {len(nombres)}: {', '.join(nombres)}")

    print("\n## FOREIGN KEYS")
    for t in TABLAS:
        c.execute(
            "SELECT conname || ' -> ' || pg_get_constraintdef(oid) FROM pg_constraint "
            "WHERE conrelid=('public.'||%s)::regclass AND contype='f' ORDER BY conname",
            [t],
        )
        for (ddl,) in c.fetchall():
            print(f"[{t}] {ddl}")

    print("\n## TABLAS")
    c.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema='public' "
        "AND table_name NOT LIKE 'django_%' AND table_name NOT LIKE 'auth_%' "
        "ORDER BY table_name"
    )
    print([r[0] for r in c.fetchall()])
