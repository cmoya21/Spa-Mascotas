URLS_SOLO_ADMIN = [
    '/api/reportes/dashboard',
    '/api/cobros/cierre-caja',
    '/api/usuarios',
    '/api/alertas/consumo-por-groomer',
]


def test_urls_admin_bloquean_groomer(client, token_groomer):
    for url in URLS_SOLO_ADMIN:
        r = client.get(url, headers={"Authorization": f"Bearer {token_groomer}"})
        assert r.status_code == 403, f"Groomer NO debería acceder a {url} (got {r.status_code})"


def test_urls_admin_bloquean_cliente(client, token_cliente):
    for url in URLS_SOLO_ADMIN:
        r = client.get(url, headers={"Authorization": f"Bearer {token_cliente}"})
        assert r.status_code == 403, f"Cliente NO debería acceder a {url} (got {r.status_code})"


def test_urls_admin_bloquean_recepcion(client, token_recep):
    urls_solo_admin = [
        '/api/reportes/dashboard',
        '/api/cobros/cierre-caja',
        '/api/usuarios',
    ]
    for url in urls_solo_admin:
        r = client.get(url, headers={"Authorization": f"Bearer {token_recep}"})
        assert r.status_code == 403, f"Recepcion NO debería acceder a {url}"


def test_groomer_no_ve_cobros(client, token_groomer):
    r = client.get('/api/cobros/pendientes', headers={"Authorization": f"Bearer {token_groomer}"})
    assert r.status_code == 403


def test_cliente_no_ve_agenda_admin(client, token_cliente):
    r = client.get('/api/agenda/semana?fecha=2025-05-27', headers={"Authorization": f"Bearer {token_cliente}"})
    assert r.status_code == 403


def test_recepcion_accede_agenda(client, token_recep):
    r = client.get('/api/agenda/semana?fecha=2025-05-27', headers={"Authorization": f"Bearer {token_recep}"})
    assert r.status_code == 200


def test_recepcion_accede_cobros(client, token_recep):
    r = client.get('/api/cobros/pendientes', headers={"Authorization": f"Bearer {token_recep}"})
    assert r.status_code == 200


def test_groomer_accede_solo_su_agenda(client, token_groomer):
    r = client.get('/api/groomers/me/agenda', headers={"Authorization": f"Bearer {token_groomer}"})
    assert r.status_code == 200


def test_cliente_accede_su_dashboard(client, token_cliente):
    r = client.get('/api/clientes/me/mascotas', headers={"Authorization": f"Bearer {token_cliente}"})
    assert r.status_code == 200


def test_cliente_accede_tienda(client, token_cliente):
    r = client.get('/api/productos', headers={"Authorization": f"Bearer {token_cliente}"})
    assert r.status_code == 200


def test_recepcion_no_gestiona_usuarios(client, token_recep):
    r = client.get('/api/usuarios', headers={"Authorization": f"Bearer {token_recep}"})
    assert r.status_code == 403


def test_admin_accede_todo(client, token_admin):
    urls_admin = [
        '/api/reportes/dashboard',
        '/api/cobros/cierre-caja',
        '/api/usuarios',
        '/api/alertas/inventario',
        '/api/cobros/pendientes',
    ]
    for url in urls_admin:
        r = client.get(url, headers={"Authorization": f"Bearer {token_admin}"})
        assert r.status_code in (200, 404), f"Admin debería acceder a {url} (got {r.status_code})"
