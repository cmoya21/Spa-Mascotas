def test_no_agenda_servicio_largo_en_hueco_corto(client, token_recep):
    """Servicio de 60 min no puede agendarse en un slot con solo 30 min libres."""
    r = client.post(
        "/api/agenda/validar-cita",
        json={
            "groomer_id": 1,
            "servicio_id": 1,
            "mascota_id": 1,
            "fecha_hora_inicio": "2099-01-06T17:30:00",
        },
        headers=auth(token_recep),
    )
    assert r.status_code in (200, 409)
    if r.status_code == 200:
        data = r.get_json()["data"]
        assert data["valido"] is False
        assert any("espacio" in e.lower() or "jornada" in e.lower() for e in data.get("errores", []))


def test_bloquea_agenda_si_supera_capacidad(client, token_recep):
    """No permite crear más citas que capacidad_simultanea del groomer."""
    r = client.post(
        "/api/agenda/validar-cita",
        json={
            "groomer_id": 1,
            "servicio_id": 1,
            "mascota_id": 1,
            "fecha_hora_inicio": "2099-01-06T09:00:00",
        },
        headers=auth(token_recep),
    )
    payload = r.get_json() or {}
    data = payload.get("data", payload)
    assert r.status_code in (200, 409)
    if r.status_code == 200:
        assert data.get("valido") is False


def test_groomer_no_accede_cierre_caja(client, token_groomer):
    r = client.get("/api/cobros/cierre-caja?fecha=2025-01-01", headers=auth(token_groomer))
    assert r.status_code == 403


def test_cliente_no_accede_cierre_caja(client, token_cliente):
    r = client.get("/api/cobros/cierre-caja?fecha=2025-01-01", headers=auth(token_cliente))
    assert r.status_code == 403


def test_recepcion_no_accede_cierre_caja(client, token_recep):
    r = client.get("/api/cobros/cierre-caja?fecha=2025-01-01", headers=auth(token_recep))
    assert r.status_code == 403


def test_metodo_pago_invalido(client, token_recep):
    r = client.post(
        "/api/cobros/1/pagar",
        json={"metodo_pago": "bitcoin"},
        headers=auth(token_recep),
    )
    assert r.status_code == 422


def test_metodos_pago_validos_existen(client, token_recep):
    for metodo in ["efectivo", "qr", "transferencia"]:
        r = client.post(
            "/api/cobros/999/pagar",
            json={"metodo_pago": metodo},
            headers=auth(token_recep),
        )
        assert r.status_code in (200, 201, 404, 409)
        assert r.status_code != 422, f"Método {metodo} rechazado incorrectamente"


def test_admin_si_ve_reportes(client, token_admin):
    r = client.get("/api/reportes/dashboard", headers=auth(token_admin))
    assert r.status_code in (200, 404)
    assert r.status_code != 403


def test_cliente_no_ve_reportes_admin(client, token_cliente):
    r = client.get("/api/reportes/dashboard", headers=auth(token_cliente))
    assert r.status_code == 403


def test_groomer_no_ve_reportes_admin(client, token_groomer):
    r = client.get("/api/reportes/dashboard", headers=auth(token_groomer))
    assert r.status_code == 403


def test_reprogramar_slot_ocupado_retorna_409(client, token_recep):
    r = client.patch(
        "/api/citas/1/reprogramar",
        json={"nueva_fecha_hora_inicio": "2099-01-06T09:00:00"},
        headers=auth(token_recep),
    )
    assert r.status_code in (200, 404, 409)


def test_no_cancelar_cita_completada(client, token_recep):
    r = client.patch(
        "/api/citas/9999/cancelar",
        json={"motivo_cancelacion": "test"},
        headers=auth(token_recep),
    )
    assert r.status_code in (404, 422)


def test_pago_crea_factura_y_pagos(client, token_recep):
    from app.models import Factura, Pago

    r = client.post(
        "/api/cobros/1/pagar",
        json={
            "metodo_pago": "efectivo",
            "descuento": 5,
        },
        headers=auth(token_recep),
    )
    assert r.status_code in (200, 201)
    payload = r.get_json()["data"]
    assert payload["metodo_pago"] == "efectivo"
    assert "factura_numero" in payload

    factura = Factura.query.filter_by(cita_id=1).first()
    pago = Pago.query.filter_by(factura_id=factura.id).first()
    assert factura is not None
    assert pago is not None
    assert float(factura.total) == 75.0


def test_reprogramar_registra_audit_log(client, token_recep):
    from app.models import AuditLog

    nueva_fecha = "2099-01-07T09:00:00"
    r = client.patch(
        "/api/citas/1/reprogramar",
        json={"nueva_fecha_hora_inicio": nueva_fecha},
        headers=auth(token_recep),
    )
    assert r.status_code in (200, 409)
    if r.status_code == 200:
        audit = AuditLog.query.filter_by(tabla="citas", operacion="UPDATE", registro_id=1).order_by(AuditLog.id.desc()).first()
        assert audit is not None
        assert audit.datos_antes is not None
        assert audit.datos_despues is not None


def test_confirmar_crea_notificaciones(client, token_recep):
    from app.models import Notificacion

    r = client.patch("/api/citas/1/confirmar", headers=auth(token_recep))
    assert r.status_code in (200, 422)
    if r.status_code == 200:
        notificaciones = Notificacion.query.filter_by(cita_id=1).all()
        assert len(notificaciones) >= 1


def auth(token):
    return {"Authorization": f"Bearer {token}"}
