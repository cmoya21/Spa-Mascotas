from tests.conftest import auth


def test_carrito_requiere_auth(client):
    r = client.get('/api/carrito/me')
    assert r.status_code == 401


def test_carrito_cliente_crea_si_no_existe(client, token_cliente):
    r = client.get('/api/carrito/me', headers=auth(token_cliente))
    assert r.status_code == 200
    assert 'items' in r.json
    assert 'subtotal' in r.json
    assert 'expires_at' in r.json


def test_agregar_item_al_carrito(client, token_cliente):
    r = client.post(
        '/api/carrito/me/items',
        json={'producto_id': 1, 'cantidad': 2},
        headers=auth(token_cliente),
    )
    assert r.status_code in (200, 201, 422)
    if r.status_code in (200, 201):
        assert r.json['total_items'] >= 1


def test_stock_insuficiente_rechazado(client, token_cliente):
    r = client.post(
        '/api/carrito/me/items',
        json={'producto_id': 1, 'cantidad': 99999},
        headers=auth(token_cliente),
    )
    assert r.status_code == 422
    assert 'stock' in str(r.json).lower()


def test_generar_whatsapp_carrito_vacio(client, token_cliente):
    client.delete('/api/carrito/me', headers=auth(token_cliente))
    r = client.post('/api/pedidos/generar-whatsapp', headers=auth(token_cliente))
    assert r.status_code == 422


def test_generar_whatsapp_mensaje_coincide_carrito(client, token_cliente):
    client.delete('/api/carrito/me', headers=auth(token_cliente))
    client.post(
        '/api/carrito/me/items',
        json={'producto_id': 1, 'cantidad': 2},
        headers=auth(token_cliente),
    )
    r = client.post('/api/pedidos/generar-whatsapp', headers=auth(token_cliente))
    assert r.status_code == 200
    data = r.json
    assert 'link_whatsapp' in data
    assert 'wa.me' in data['link_whatsapp']
    assert 'mensaje_preview' in data
    assert 'items' in data
    for item in data['items']:
        assert item['nombre'] in data['mensaje_preview']
    subtotal_calculado = sum(item['subtotal'] for item in data['items'])
    assert abs(subtotal_calculado - data['subtotal']) < 0.01


def test_link_whatsapp_es_url_valida(client, token_cliente):
    client.delete('/api/carrito/me', headers=auth(token_cliente))
    client.post(
        '/api/carrito/me/items',
        json={'producto_id': 1, 'cantidad': 1},
        headers=auth(token_cliente),
    )
    r = client.post('/api/pedidos/generar-whatsapp', headers=auth(token_cliente))
    assert r.status_code == 200
    link = r.json['link_whatsapp']
    assert link.startswith('https://wa.me/')
    assert 'text=' in link


def test_pedidos_historial_cliente(client, token_cliente):
    r = client.get('/api/pedidos/me', headers=auth(token_cliente))
    assert r.status_code == 200
    assert isinstance(r.json, list)
