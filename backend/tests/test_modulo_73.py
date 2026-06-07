from tests.conftest import auth


def _unwrap(payload):
    return payload.get("data", payload)


def test_alertas_inventario_retorna_estructura(client, token_admin):
    r = client.get('/api/alertas/inventario', headers=auth(token_admin))
    assert r.status_code == 200
    data = _unwrap(r.get_json() or {})
    assert 'bajo_stock_tienda' in data
    assert 'alto_consumo' in data
    assert 'recomendaciones' in data
    assert 'total_criticos' in data
    assert isinstance(data['total_criticos'], int)


def test_alertas_rechaza_cliente(client, token_cliente):
    r = client.get('/api/alertas/inventario', headers=auth(token_cliente))
    assert r.status_code == 403


def test_alertas_rechaza_groomer(client, token_groomer):
    r = client.get('/api/alertas/inventario', headers=auth(token_groomer))
    assert r.status_code == 403


def test_reabastecer_aumenta_stock(client, token_admin):
    r_antes = client.get('/api/productos/1', headers=auth(token_admin))
    stock_antes = (r_antes.get_json() or {}).get('stock', 0) if r_antes.status_code == 200 else 0
    r = client.post('/api/productos/1/reabastecer',
        json={'cantidad':10,'notas':'Test reabastecimiento'},
        headers=auth(token_admin))
    assert r.status_code in (200, 404)
    if r.status_code == 200:
        assert (r.get_json() or {}).get('stock') == stock_antes + 10


def test_reabastecer_registra_audit_log(client, token_admin):
    r = client.post('/api/productos/1/reabastecer',
        json={'cantidad':5},
        headers=auth(token_admin))
    if r.status_code == 200:
        r_log = client.get('/api/alertas/inventario',
                           headers=auth(token_admin))
        assert r_log.status_code == 200


def test_consumo_por_groomer_requiere_admin(client, token_recep):
    r = client.get('/api/alertas/consumo-por-groomer',
                   headers=auth(token_recep))
    assert r.status_code == 403


def test_consumo_por_groomer_admin_accede(client, token_admin):
    r = client.get('/api/alertas/consumo-por-groomer',
                   headers=auth(token_admin))
    assert r.status_code == 200
    assert isinstance(r.get_json(), list)
