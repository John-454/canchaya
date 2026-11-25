from django.db import migrations


class Migration(migrations.Migration):
    """Crea la función usada por las `ExclusionConstraint` (R2).

    PostgreSQL no tiene un tipo `timerange`. `canchaya_timerange(start, end)`
    devuelve un `int4range` semiabierto `[start, end)` en segundos desde
    medianoche, que sí soporta el operador `&&` dentro de `EXCLUDE USING gist`
    (gracias a `btree_gist`). Es IMMUTABLE para poder usarse en constraints.

    La función debe existir ANTES de `fields.0002_initial` (que crea las
    exclusiones) y `bookings.0003_initial`, por eso es la migración 0002.
    """

    dependencies = [
        ("fields", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                CREATE OR REPLACE FUNCTION canchaya_timerange(p_start TIME, p_end TIME)
                RETURNS int4range
                LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE
                AS $$
                    SELECT int4range(
                        EXTRACT(EPOCH FROM p_start)::int,
                        EXTRACT(EPOCH FROM p_end)::int,
                        '[)'
                    );
                $$;
            """,
            reverse_sql="DROP FUNCTION IF EXISTS canchaya_timerange(TIME, TIME);",
        ),
    ]
