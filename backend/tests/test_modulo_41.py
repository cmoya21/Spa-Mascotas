import io

from tests.conftest import auth


def test_crear_mascota_sin_archivos(client, token_cliente):
    r = client.post(
        '/api/clientes/me/mascotas',
        json={'nombre': 'Rex', 'especie': 'perro', 'temperamento': 'tranquilo', 'peso_kg': 8.0},
        headers=auth(token_cliente),
    )
    assert r.status_code == 201
    data = r.json
    assert data['nombre'] == 'Rex'
    assert 'id' in data


def test_mascota_especie_invalida(client, token_cliente):
    r = client.post(
        '/api/clientes/me/mascotas',
        json={'nombre': 'Rex', 'especie': 'dragon', 'temperamento': 'tranquilo'},
        headers=auth(token_cliente),
    )
    assert r.status_code == 422


def test_mascota_sin_nombre(client, token_cliente):
    r = client.post(
        '/api/clientes/me/mascotas',
        json={'especie': 'perro', 'temperamento': 'tranquilo'},
        headers=auth(token_cliente),
    )
    assert r.status_code == 422


def test_un_cliente_puede_tener_varias_mascotas(client, token_cliente):
    nombres = ['Fido', 'Luna', 'Max']
    ids = []
    for nombre in nombres:
        r = client.post(
            '/api/clientes/me/mascotas',
            json={'nombre': nombre, 'especie': 'perro', 'temperamento': 'jugueton'},
            headers=auth(token_cliente),
        )
        assert r.status_code == 201
        ids.append(r.json['id'])
    r2 = client.get('/api/clientes/me/mascotas', headers=auth(token_cliente))
    assert r2.status_code == 200
    assert len(r2.json['data']['mascotas']) >= 3


def test_cliente_no_edita_mascota_ajena(client, token_cliente):
    r = client.put(
        '/api/clientes/me/mascotas/9999',
        json={'nombre': 'Hacker'},
        headers=auth(token_cliente),
    )
    assert r.status_code == 404


def test_upload_foto_extension_invalida(client, token_cliente):
    r_mascota = client.post(
        '/api/clientes/me/mascotas',
        json={'nombre': 'TestFoto', 'especie': 'gato', 'temperamento': 'tranquilo'},
        headers=auth(token_cliente),
    )
    mid = r_mascota.json['id']
    data = {'foto': (io.BytesIO(b'fakecontent'), 'virus.exe')}
    r = client.put(
        f'/api/clientes/me/mascotas/{mid}',
        data=data,
        content_type='multipart/form-data',
        headers=auth(token_cliente),
    )
    assert r.status_code == 422
