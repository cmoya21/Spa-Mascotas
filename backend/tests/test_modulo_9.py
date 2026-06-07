from datetime import datetime, timezone
from unittest.mock import MagicMock

from tests.conftest import auth


def test_worker_procesa_notificacion_pendiente(client):
    from app.extensions import db
    from app.models.notificacion import Notificacion
    from app.utils.notif_worker import procesar_notificaciones

    with client.application.app_context():
        notif = Notificacion(
            tipo_canal="whatsapp",
            tipo_evento="listo_recoger",
            destino="59170000000",
            mensaje="Test listo para recoger",
            fecha_programacion=datetime(2020, 1, 1, tzinfo=timezone.utc),
            estado="pendiente",
            reintentos=0,
        )
        db.session.add(notif)
        db.session.commit()
        notif_id = notif.id

    procesar_notificaciones()

    with client.application.app_context():
        notif_updated = Notificacion.query.get(notif_id)
        assert notif_updated.estado == "enviado"
        assert notif_updated.fecha_envio is not None


def test_notificaciones_cliente_requiere_auth(client):
    r = client.get("/api/notificaciones/me")
    assert r.status_code == 401


def test_notificaciones_cliente_retorna_lista(client, token_cliente):
    r = client.get("/api/notificaciones/me", headers=auth(token_cliente))
    assert r.status_code == 200
    assert isinstance(r.json, list)


def test_notificaciones_admin_requiere_rol_cliente(client, token_cliente):
    r = client.get("/api/notificaciones/admin", headers=auth(token_cliente))
    assert r.status_code == 403


def test_notificaciones_admin_requiere_rol_groomer(client, token_groomer):
    r = client.get("/api/notificaciones/admin", headers=auth(token_groomer))
    assert r.status_code == 403


def test_stats_notificaciones_admin(client, token_admin):
    r = client.get("/api/notificaciones/stats", headers=auth(token_admin))
    assert r.status_code == 200
    data = r.json
    assert "pendientes" in data
    assert "enviadas" in data
    assert "fallidas" in data
    assert "listo_recoger_enviadas" in data


def test_reenviar_notificacion_fallida(client, token_admin):
    from app.extensions import db
    from app.models.notificacion import Notificacion

    with client.application.app_context():
        notif = Notificacion(
            tipo_canal="email",
            tipo_evento="confirmacion",
            destino="test@test.com",
            mensaje="Test",
            fecha_programacion=datetime.now(timezone.utc),
            estado="fallido",
            reintentos=3,
        )
        db.session.add(notif)
        db.session.commit()
        nid = notif.id

    r = client.post(f"/api/notificaciones/reenviar/{nid}", headers=auth(token_admin))
    assert r.status_code == 200

    with client.application.app_context():
        notif_updated = Notificacion.query.get(nid)
        assert notif_updated.estado == "pendiente"
        assert notif_updated.reintentos == 0
        assert notif_updated.error_mensaje is None


def test_plantilla_listo_recoger():
    from app.utils.plantillas_notif import mensaje_listo_recoger

    msg = mensaje_listo_recoger("Luna", "Baño completo")
    assert "Luna" in msg
    assert "lista" in msg.lower() or "listo" in msg.lower()


def test_plantilla_recordatorio_24h():
    from app.utils.plantillas_notif import mensaje_recordatorio_24h

    msg = mensaje_recordatorio_24h("Max", "Corte", "10:00")
    assert "Max" in msg
    assert "10:00" in msg


def test_plantilla_bajo_stock():
    from app.utils.plantillas_notif import mensaje_bajo_stock

    msg = mensaje_bajo_stock("Shampoo", 2, 5)
    assert "Shampoo" in msg
    assert "2" in msg


def test_crear_notificacion_helper(client):
    from app.utils.crear_notificacion import crear_notificacion

    cliente_mock = MagicMock()
    cliente_mock.id = 1
    cliente_mock.canal_notificacion = "whatsapp"
    cliente_mock.telefono = "59170000000"
    cliente_mock.usuario = None

    with client.application.app_context():
        notif = crear_notificacion(
            cliente=cliente_mock,
            tipo_evento="listo_recoger",
            mensaje="Test mensaje",
        )
        assert notif is not None
        assert notif.tipo_evento == "listo_recoger"
        assert notif.estado == "pendiente"


def test_alertas_bajo_stock_inserta_notificaciones(client, token_admin):
    from app.extensions import db
    from app.models.inventario import Producto
    from app.models.notificacion import Notificacion

    with client.application.app_context():
        producto = Producto(
            nombre="Shampoo alertado",
            sku="SH-AL-001",
            precio_base=20,
            stock=1,
            stock_minimo=5,
            activo=True,
        )
        db.session.add(producto)
        db.session.commit()

    r = client.get("/api/alertas/inventario", headers=auth(token_admin))
    assert r.status_code == 200

    with client.application.app_context():
        noti = Notificacion.query.filter_by(tipo_evento="bajo_stock").first()
        assert noti is not None


def test_solicitud_cita_crea_notificacion_revision(client, token_cliente):
    from app.extensions import db
    from app.models.agenda import DisponibilidadGroomer, Servicio
    from app.models.mascota import Mascota
    from app.models.notificacion import Notificacion
    from app.models.usuario import Groomer

    with client.application.app_context():
        mascota = Mascota.query.first()
        servicio = Servicio.query.first()
        groomer = Groomer.query.first()
        assert mascota is not None
        assert servicio is not None
        assert groomer is not None
        mascota_id = mascota.id
        servicio_id = servicio.id

        dia_semana = int(datetime(2099, 3, 10).strftime("%w"))
        disponibilidad = DisponibilidadGroomer.query.filter_by(groomer_id=groomer.id, dia_semana=dia_semana).first()
        if not disponibilidad:
            db.session.add(
                DisponibilidadGroomer(
                    groomer_id=groomer.id,
                    dia_semana=dia_semana,
                    hora_inicio=datetime.strptime("09:00", "%H:%M").time(),
                    hora_fin=datetime.strptime("18:00", "%H:%M").time(),
                    activo=True,
                )
            )
            db.session.commit()

    r = client.post(
        "/api/solicitudes-cita",
        json={
            "mascota_id": mascota_id,
            "servicio_id": servicio_id,
            "fecha_preferida": "2099-03-10",
            "franja": "manana",
        },
        headers=auth(token_cliente),
    )
    assert r.status_code in (200, 201)
    payload = r.get_json() or {}
    data = payload.get("data", payload)
    cita_id = data["cita_id"]

    with client.application.app_context():
        notif = Notificacion.query.filter_by(cita_id=cita_id, tipo_evento="solicitud_revision").first()
        assert notif is not None


def test_confirmar_cita_crea_recordatorios(client, token_admin):
    from app.extensions import db
    from app.models.agenda import Cita
    from app.models.notificacion import Notificacion

    with client.application.app_context():
        cita = Cita.query.first()
        assert cita is not None
        cita.estado = "agendada"
        db.session.commit()
        cita_id = cita.id

    r = client.patch(f"/api/citas/{cita_id}/confirmar", headers=auth(token_admin))
    assert r.status_code == 200

    with client.application.app_context():
        tipos = {item.tipo_evento for item in Notificacion.query.filter_by(cita_id=cita_id).all()}
        assert "confirmacion" in tipos
        assert "recordatorio_24h" in tipos
        assert "recordatorio_2h" in tipos


def test_cerrar_ficha_crea_listo_recoger_y_stats(client, token_groomer, token_admin):
    from app.extensions import db
    from app.models.agenda import Cita, Servicio
    from app.models.grooming import ChecklistItemTemplate, FichaChecklist, FichaGrooming, FotoFicha
    from app.models.mascota import Mascota
    from app.models.notificacion import Notificacion
    from app.models.usuario import Groomer
    from app.utils.notif_worker import procesar_notificaciones

    with client.application.app_context():
        cita = Cita.query.first()
        groomer = Groomer.query.first()
        mascota = Mascota.query.first()
        servicio = Servicio.query.first()
        assert cita is not None and groomer is not None and mascota is not None and servicio is not None

        cita.estado = "en_progreso"
        ficha = FichaGrooming(cita_id=cita.id, groomer_id=groomer.id)
        db.session.add(ficha)
        db.session.flush()

        template = ChecklistItemTemplate(servicio_id=servicio.id, nombre="Secado", activo=True)
        db.session.add(template)
        db.session.flush()

        db.session.add(FichaChecklist(ficha_id=ficha.id, item_id=template.id, completado=True, completado_en=datetime.now(timezone.utc)))
        db.session.add(FotoFicha(ficha_id=ficha.id, url="https://img/antes.jpg", tipo="antes"))
        db.session.add(FotoFicha(ficha_id=ficha.id, url="https://img/despues.jpg", tipo="despues"))
        db.session.commit()
        ficha_id = ficha.id

    r = client.patch(f"/api/grooming/fichas/{ficha_id}/cerrar", json={"estado_final": "Ok"}, headers=auth(token_groomer))
    assert r.status_code == 200

    procesar_notificaciones()

    r_stats = client.get("/api/notificaciones/stats", headers=auth(token_admin))
    assert r_stats.status_code == 200
    assert r_stats.json["listo_recoger_enviadas"] > 0


def test_pago_registrado_crea_notificacion(client, token_admin):
    from app.extensions import db
    from app.models.agenda import Cita
    from app.models.facturacion import Factura
    from app.models.notificacion import Notificacion

    with client.application.app_context():
        cita = Cita.query.first()
        assert cita is not None
        cita.estado = "completada"
        db.session.commit()
        cita_id = cita.id

    r = client.post(
        f"/api/cobros/{cita_id}/pagar",
        json={"metodo_pago": "efectivo"},
        headers=auth(token_admin),
    )
    assert r.status_code == 200

    with client.application.app_context():
        factura = Factura.query.filter_by(cita_id=cita_id).first()
        assert factura is not None
        notif = Notificacion.query.filter_by(cita_id=cita_id, tipo_evento="pago_registrado").first()
        assert notif is not None
