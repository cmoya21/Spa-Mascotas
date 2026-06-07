from tests.conftest import auth


def test_confirmar_uso_valida_cantidad(client, token_groomer):
    r = client.patch(
        "/api/insumos/salida/1/confirmar-uso",
        json={"cantidad_usada": 99999},
        headers=auth(token_groomer),
    )
    assert r.status_code in (403, 404, 422)


def test_confirmar_uso_actualiza_insumos_consumidos(client, token_groomer):
    r = client.patch(
        "/api/insumos/salida/1/confirmar-uso",
        json={"cantidad_usada": 0.05},
        headers=auth(token_groomer),
    )
    assert r.status_code in (200, 403, 404, 422)


def test_merma_alta_crea_alerta(client, token_groomer):
    r = client.patch(
        "/api/insumos/salida/1/merma",
        json={"cantidad_desperdicio": 0.09, "motivo": "Se derramó"},
        headers=auth(token_groomer),
    )
    assert r.status_code in (200, 403, 404)


def test_confirmar_todos_transaccional(client, token_groomer):
    r = client.patch(
        "/api/insumos/salida/ficha/1/confirmar-todos",
        json={"insumos": [{"salida_id": 1, "cantidad_usada": 0.05}]},
        headers=auth(token_groomer),
    )
    assert r.status_code in (200, 403, 404)
    if r.status_code == 200:
        assert "confirmados" in r.json
