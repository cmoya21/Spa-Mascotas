from tests.conftest import auth


def test_catalogo_publico_sin_auth(client):
    r = client.get('/api/productos')
    assert r.status_code == 200
    assert 'productos' in r.json


def test_categorias_publicas(client):
    r = client.get('/api/categorias')
    assert r.status_code == 200
    assert isinstance(r.json, list)
    assert len(r.json) >= 5


def test_crear_producto_requiere_admin(client, token_cliente):
    r = client.post('/api/productos',
        json={'nombre':'Test','sku':'TST-001',
              'precio_base':10.0,'stock':5,'stock_minimo':1},
        headers=auth(token_cliente))
    assert r.status_code == 403


def test_crear_producto_admin_ok(client, token_admin):
    r = client.post('/api/productos',
        json={'nombre':'Producto Test 81','sku':'TST-8100',
              'precio_base':15.0,'stock':10,'stock_minimo':2},
        headers=auth(token_admin))
    assert r.status_code in (200, 201)


def test_sku_duplicado_rechazado(client, token_admin):
    client.post('/api/productos',
        json={'nombre':'Dup1','sku':'DUP-81-001',
              'precio_base':10.0,'stock':5,'stock_minimo':1},
        headers=auth(token_admin))
    r = client.post('/api/productos',
        json={'nombre':'Dup2','sku':'DUP-81-001',
              'precio_base':10.0,'stock':5,'stock_minimo':1},
        headers=auth(token_admin))
    assert r.status_code == 422


def test_ajuste_stock_funciona(client, token_admin):
    r_prod = client.post('/api/productos',
        json={'nombre':'StockTest81','sku':'STK-8100',
              'precio_base':10.0,'stock':5,'stock_minimo':1},
        headers=auth(token_admin))
    if r_prod.status_code in (200, 201):
        pid = r_prod.json['id']
        r = client.patch(f'/api/productos/{pid}/stock',
            json={'cantidad':10,'operacion':'agregar'},
            headers=auth(token_admin))
        assert r.status_code == 200
        assert r.json['stock_nuevo'] == 15


def test_filtrar_por_categoria(client):
    r_cats = client.get('/api/categorias')
    if r_cats.status_code == 200 and r_cats.json:
        cat_id = r_cats.json[0]['id']
        r = client.get(f'/api/productos?categoria={cat_id}')
        assert r.status_code == 200


def test_busqueda_productos(client):
    r = client.get('/api/productos?q=shampoo')
    assert r.status_code == 200


def test_paginacion_productos(client):
    r = client.get('/api/productos?page=1&per_page=5')
    assert r.status_code == 200
    data = r.json
    assert 'total' in data
    assert len(data['productos']) <= 5
