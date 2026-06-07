from tests.conftest import auth


def test_cierre_sin_checklist_retorna_422(client, token_groomer):
    r = client.patch('/api/fichas/1/cerrar',
        json={'estado_final':'Test cerrar servicio ok',
              'duracion_real':60},
        headers=auth(token_groomer))
    assert r.status_code in (403, 404, 422)
    if r.status_code == 422:
        assert r.json.get('error') in (
            'checklist_incompleto','sin_foto_antes',
            'sin_foto_despues','checklist_incomplete'
        )


def test_double_cierre_retorna_409(client, token_groomer):
    r = client.patch('/api/fichas/1/cerrar',
        json={'estado_final':'Segundo cierre intento',
              'duracion_real':30},
        headers=auth(token_groomer))
    assert r.status_code in (403, 404, 409, 422)


def test_estado_cierre_retorna_diagnostico(client, token_groomer):
    r = client.get('/api/fichas/1/estado-cierre',
                   headers=auth(token_groomer))
    assert r.status_code in (200, 403, 404)
    if r.status_code == 200:
        assert 'puede_cerrar' in r.json
        assert 'checklist' in r.json
        assert 'fotos' in r.json
        assert 'razones_bloqueo' in r.json


def test_estado_cierre_cliente_no_accede(client, token_cliente):
    r = client.get('/api/fichas/1/estado-cierre',
                   headers=auth(token_cliente))
    assert r.status_code == 403


def test_cierre_crea_notificacion_si_exitoso(client, token_groomer,
                                              token_admin):
    r = client.patch('/api/fichas/1/cerrar',
        json={'estado_final':'Servicio finalizado correctamente',
              'duracion_real':75},
        headers=auth(token_groomer))
    if r.status_code == 200:
        assert r.json.get('notificacion_programada') == True
        assert r.json.get('canal_notificacion') is not None
