import io
from datetime import datetime


def _ensure_support_data(db):
    from app.models import ChecklistItemTemplate, Producto, Rol, Usuario, Groomer, Cliente
    from app.models.agenda import Cita, DisponibilidadGroomer
    from app.models.mascota import MascotaDueno
    from app.models.usuario import Cliente as ClienteModel

    template1 = ChecklistItemTemplate.query.filter_by(servicio_id=1, nombre="Cepillado inicial").first()
    if not template1:
        template1 = ChecklistItemTemplate(servicio_id=1, nombre="Cepillado inicial", requiere_obs=True, orden=1, activo=True)
        db.session.add(template1)
    template2 = ChecklistItemTemplate.query.filter_by(servicio_id=1, nombre="Secado final").first()
    if not template2:
        template2 = ChecklistItemTemplate(servicio_id=1, nombre="Secado final", requiere_obs=False, orden=2, activo=True)
        db.session.add(template2)

    producto = Producto.query.filter_by(sku="GROOM-001").first()
    if not producto:
        producto = Producto(nombre="Shampoo premium", sku="GROOM-001", precio_base=25.0, stock=10, stock_minimo=2, activo=True)
        db.session.add(producto)

    db.session.commit()
    return producto


def test_agenda_groomer_solo_muestra_citas_propias(client, token_groomer):
    from app.extensions import db
    from app.models import Groomer, Usuario
    from app.models.agenda import Cita
    from app.models.rol import Rol

    _ensure_support_data(db)

    other_role = Rol.query.filter_by(nombre="Groomer").first()
    other_user = Usuario(email="otro-groomer@test.com", rol_id=other_role.id, estado_activo=True)
    other_user.set_password("pass")
    db.session.add(other_user)
    db.session.flush()
    other_groomer = Groomer(usuario_id=other_user.id, nombre="Bruno", apellido="Mora", capacidad_simultanea=1, estado_activo=True)
    db.session.add(other_groomer)
    db.session.flush()

    cita_ajena = Cita(
        mascota_id=1,
        groomer_id=other_groomer.id,
        servicio_id=1,
        fecha_hora_inicio=datetime(2099, 1, 6, 12, 0, 0),
        fecha_hora_fin=datetime(2099, 1, 6, 13, 0, 0),
        duracion_estimada=60,
        precio_estimado=80.0,
        estado="agendada",
    )
    db.session.add(cita_ajena)
    db.session.commit()

    response = client.get("/api/groomers/me/agenda?fecha=2099-01-06", headers=auth(token_groomer))
    assert response.status_code == 200
    citas = response.get_json()["data"]["citas"]
    assert any(item["id"] == 1 for item in citas)
    assert all(item["groomer_id"] != other_groomer.id for item in citas)
    assert all("factura" not in item for item in citas)


def test_checklist_bloquea_cierre_y_luego_permite_stock_y_notificacion(client, token_groomer):
    from app.extensions import db
    from app.models import AuditLog, Notificacion, Producto
    from app.models.agenda import Cita
    from app.models.grooming import FichaGrooming, FichaChecklist

    producto = _ensure_support_data(db)

    crear_ficha = client.post(
        "/api/fichas",
        json={
            "cita_id": 1,
            "estado_inicial": "Llega limpia",
            "temperatura_ingreso": 38.1,
            "peso_momento_servicio": 4.2,
            "raza_tamano_momento": "Pequeno",
            "notas_internas": "Cliente puntual",
        },
        headers=auth(token_groomer),
    )
    assert crear_ficha.status_code == 201
    ficha_id = crear_ficha.get_json()["data"]["ficha"]["id"]

    cierre_bloqueado = client.patch(
        f"/api/fichas/{ficha_id}/cerrar",
        json={"estado_final": "Lista", "observaciones_final": "Todo bien", "duracion_real": 70},
        headers=auth(token_groomer),
    )
    assert cierre_bloqueado.status_code == 422

    ficha_resp = client.get(f"/api/fichas/{ficha_id}", headers=auth(token_groomer))
    items = ficha_resp.get_json()["data"]["ficha"]["checklist"]
    assert len(items) >= 2

    for item in items:
        if item["requiere_obs"]:
            obs_response = client.patch(
                f"/api/fichas/{ficha_id}/checklist/{item['item_id']}",
                json={"completado": True},
                headers=auth(token_groomer),
            )
            assert obs_response.status_code == 422
        ok_response = client.patch(
            f"/api/fichas/{ficha_id}/checklist/{item['item_id']}",
            json={"completado": True, "observacion": "OK" if item["requiere_obs"] else None},
            headers=auth(token_groomer),
        )
        assert ok_response.status_code == 200

    before_photo = client.post(
        f"/api/fichas/{ficha_id}/fotos",
        data={"tipo": "antes", "archivo": (io.BytesIO(b"before"), "before.png")},
        headers=auth(token_groomer),
        content_type="multipart/form-data",
    )
    assert before_photo.status_code == 201

    after_photo = client.post(
        f"/api/fichas/{ficha_id}/fotos",
        data={"tipo": "despues", "archivo": (io.BytesIO(b"after"), "after.png")},
        headers=auth(token_groomer),
        content_type="multipart/form-data",
    )
    assert after_photo.status_code == 201

    insumos = client.patch(
        f"/api/fichas/{ficha_id}/insumos",
        json={"insumos": [{"producto_id": producto.id, "cantidad": 0.5, "devuelto": 0, "desperdicio": 0}]},
        headers=auth(token_groomer),
    )
    assert insumos.status_code == 200

    audit = AuditLog.query.filter_by(tabla="fichas_grooming", registro_id=ficha_id).order_by(AuditLog.id.desc()).first()
    assert audit is not None
    assert audit.groomer_id is not None

    ficha_detail = client.get(f"/api/fichas/{ficha_id}", headers=auth(token_groomer)).get_json()["data"]["ficha"]
    assert ficha_detail["checklist_completo"] is True
    assert len(ficha_detail["fotos"]["antes"]) >= 1
    assert len(ficha_detail["fotos"]["despues"]) >= 1

    stock_antes = Producto.query.filter_by(id=producto.id).first().stock
    cierre = client.patch(
        f"/api/fichas/{ficha_id}/cerrar",
        json={"estado_final": "Listo", "observaciones_final": "Sin novedades", "duracion_real": 75},
        headers=auth(token_groomer),
    )
    assert cierre.status_code == 200

    stock_despues = Producto.query.filter_by(id=producto.id).first().stock
    assert float(stock_antes) - float(stock_despues) == 0.5

    notificaciones = Notificacion.query.filter_by(cita_id=1, tipo_evento="listo_recoger").all()
    assert len(notificaciones) >= 1

    cita = Cita.query.filter_by(id=1).first()
    assert cita.estado == "completada"


def test_insumos_disponibles_autocomplete_muestra_stock(client, token_groomer):
    from app.extensions import db
    producto = _ensure_support_data(db)

    response = client.get("/api/fichas/1/insumos-disponibles?q=shampoo", headers=auth(token_groomer))
    assert response.status_code == 200
    productos = response.get_json()["data"]["productos"]
    assert any(item["id"] == producto.id and item["stock"] > 0 for item in productos)


def test_groomer_no_ve_reportes_financieros(client, token_groomer):
    response = client.get("/api/reportes/dashboard", headers=auth(token_groomer))
    assert response.status_code == 403


def auth(token):
    return {"Authorization": f"Bearer {token}"}
