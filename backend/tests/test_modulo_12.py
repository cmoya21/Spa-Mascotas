from tests.conftest import auth


def _payload(response):
    data = response.get_json() or {}
    return data.get("data", data)


# Admin

def test_ventas_solo_admin(client, token_recep):
    r = client.get("/api/reportes/ventas", headers=auth(token_recep))
    assert r.status_code == 403


def test_ventas_admin_ok(client, token_admin):
    r = client.get("/api/reportes/ventas", headers=auth(token_admin))
    assert r.status_code == 200


def test_ranking_solo_admin(client, token_cliente):
    r = client.get("/api/reportes/ranking-rentabilidad", headers=auth(token_cliente))
    assert r.status_code == 403


def test_ocupacion_solo_admin(client, token_groomer):
    r = client.get("/api/reportes/ocupacion", headers=auth(token_groomer))
    assert r.status_code == 403


def test_auditoria_insumos_solo_admin(client, token_recep):
    r = client.get("/api/reportes/auditoria-insumos", headers=auth(token_recep))
    assert r.status_code == 403


# Recepcion

def test_cronograma_recepcion_ok(client, token_recep):
    r = client.get("/api/reportes/cronograma-diario", headers=auth(token_recep))
    assert r.status_code == 200
    payload = _payload(r)
    assert isinstance(payload.get("items"), list)


def test_cronograma_cliente_bloqueado(client, token_cliente):
    r = client.get("/api/reportes/cronograma-diario", headers=auth(token_cliente))
    assert r.status_code == 403


def test_cancelaciones_recepcion_ok(client, token_recep):
    r = client.get("/api/reportes/cancelaciones", headers=auth(token_recep))
    assert r.status_code == 200


# Groomer

def test_productividad_solo_groomer(client, token_cliente):
    r = client.get("/api/reportes/groomer/productividad", headers=auth(token_cliente))
    assert r.status_code == 403


def test_productividad_groomer_ok(client, token_groomer):
    r = client.get("/api/reportes/groomer/productividad", headers=auth(token_groomer))
    assert r.status_code == 200


def test_historial_servicios_groomer(client, token_groomer):
    r = client.get("/api/reportes/groomer/historial-servicios", headers=auth(token_groomer))
    assert r.status_code == 200


# Cliente

def test_historial_mascota_cliente_ok(client, token_cliente):
    r = client.get("/api/reportes/cliente/historial-mascota/1", headers=auth(token_cliente))
    assert r.status_code in (200, 404)


def test_historial_mascota_ajena_bloqueada(client, token_cliente):
    r = client.get("/api/reportes/cliente/historial-mascota/9999", headers=auth(token_cliente))
    assert r.status_code == 404


def test_galeria_cliente_ok(client, token_cliente):
    r = client.get("/api/reportes/cliente/galeria/1", headers=auth(token_cliente))
    assert r.status_code in (200, 404)


# Autoevaluacion #11

def test_cliente_no_ve_ventas_admin(client, token_cliente):
    for url in [
        "/api/reportes/ventas",
        "/api/reportes/ranking-rentabilidad",
        "/api/reportes/ocupacion",
        "/api/reportes/auditoria-insumos",
    ]:
        r = client.get(url, headers=auth(token_cliente))
        assert r.status_code == 403, f"Cliente NO debe ver {url} (got {r.status_code})"


def test_groomer_no_ve_reportes_financieros(client, token_groomer):
    for url in [
        "/api/reportes/ventas",
        "/api/reportes/ranking-rentabilidad",
    ]:
        r = client.get(url, headers=auth(token_groomer))
        assert r.status_code == 403
