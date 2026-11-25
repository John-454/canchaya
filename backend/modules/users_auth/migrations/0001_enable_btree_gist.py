from django.db import migrations


class Migration(migrations.Migration):
    """Extensiones requeridas por el modelo de datos."""

    initial = True
    dependencies = []
    # Cites no se usa: correo es CITEXT/VARCHAR UNIQUE en la spec, pero Django
    # no soporta CITEXT nativamente; se guarda normalizado en minúsculas
    # (ver services de users_auth). Por eso solo se habilita btree_gist.
    operations = [
        migrations.RunSQL(
            sql="CREATE EXTENSION IF NOT EXISTS btree_gist;",
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
