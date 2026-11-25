"""Elimina (solo si están vacías) las tablas del esquema manual previo.

Se ejecuta una sola vez, antes de `manage.py migrate`.
Aborta si alguna tabla tiene filas, para no destruir datos.
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

import django  # noqa: E402

django.setup()

from django.db import connection, transaction  # noqa: E402

TABLAS = [
    "reservas",
    "tarifas",
    "horarios_operacion",
    "imagenes_cancha",
    "canchas",
    "usuarios",
]


def main() -> None:
    with transaction.atomic():
        with connection.cursor() as c:
            for t in TABLAS:
                c.execute("SELECT to_regclass(%s)::text", [f"public.{t}"])
                if not c.fetchone()[0]:
                    print(f"  {t:20s} no existe, se omite")
                    continue
                c.execute(f"SELECT count(*) FROM public.{t}")
                filas = c.fetchone()[0]
                if filas:
                    raise SystemExit(f"ABORTADO: {t} tiene {filas} filas. No se borra nada.")
                c.execute(f'DROP TABLE public."{t}" CASCADE')
                print(f"  {t:20s} eliminada (estaba vacía)")

            c.execute("SELECT to_regprocedure('public.canchaya_timerange(time,time)')::text")
            if c.fetchone()[0]:
                c.execute("DROP FUNCTION public.canchaya_timerange(TIME, TIME)")
                print("  funcion canchaya_timerange eliminada")

    print("Listo: esquema manual retirado.")


if __name__ == "__main__":
    main()
