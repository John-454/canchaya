import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_health_ok(client):
    resp = client.get("/api/v1/health/")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "database": True}


@pytest.mark.django_db
def test_urls_v1_montadas(client):
    """Todas las rutas de §5 existen; las no implementadas devuelven 501."""
    implementadas = {
        # Iteración 2-4: auth, panel de campos, reservas y finanzas (exigen JWT)
        "auth-sync": {405},
        "auth-me": {401},
        "admin-field": {401},
        "admin-field-images": {401},
        "admin-field-schedules": {401},
        "admin-field-rates": {401},
        "admin-field-rates-preview": {401},
        "admin-bookings": {401},
        "admin-finance-dashboard": {401},
        "admin-finance-summary": {401},
    }
    for name, codigos in implementadas.items():
        ruta = reverse(name)
        assert ruta.startswith("/api/v1/"), name
        assert client.get(ruta).status_code in codigos, (name, client.get(ruta).status_code)


@pytest.mark.django_db
def test_btree_gist_instalado(db):
    from django.db import connection

    with connection.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_extension WHERE extname = 'btree_gist'")
        assert cur.fetchone() == (1,)


@pytest.mark.django_db
def test_funcion_timerange_existe(db):
    from django.db import connection

    with connection.cursor() as cur:
        cur.execute("SELECT canchaya_timerange('08:00'::time, '10:00'::time)::text")
        assert cur.fetchone()[0] == "[28800,36000)"


@pytest.mark.django_db
def test_exclusion_constraints_creadas(db):
    from django.db import connection

    with connection.cursor() as cur:
        cur.execute("""
            SELECT conname FROM pg_constraint
            WHERE contype = 'x' AND conname LIKE 'ex_%%'
            ORDER BY conname
            """)
        nombres = [r[0] for r in cur.fetchall()]
    assert nombres == [
        "ex_horarios_no_solape",
        "ex_reservas_no_solape",
        "ex_tarifas_especial_no_solape",
        "ex_tarifas_semanal_no_solape",
    ]
