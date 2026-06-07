from datetime import datetime
from io import BytesIO

import pytest


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def modulo_62_seed(app):
    with app.app_context():
        from app.extensions import db
        from app.models.agenda import Cita, Servicio
        from app.models.grooming import ChecklistItemTemplate, FichaChecklist, FichaGrooming
        from app.models.inventario import Producto
        from app.models.mascota import Mascota, MascotaDueno
        from app.models.usuario import Cliente, Groomer, Usuario

        groomer = Groomer.query.join(Usuario).filter(Usuario.email == "groomer@test.com").first()
        cliente = Cliente.query.join(Usuario).filter(Usuario.email == "cliente@test.com").first()
        servicio = Servicio.query.first()

        if not groomer or not cliente or not servicio:
            raise RuntimeError("Datos base faltantes para el módulo 6.2")

        mascota = Mascota.query.filter_by(nombre="Luna modulo 62").first()
        if not mascota:
            mascota = Mascota(
                nombre="Luna modulo 62",
                especie="perro",
                raza="Poodle",
                peso_kg=4.2,
                temperamento="tranquilo",
                alergias_conocidas="shampoo fragancia",
                restricciones_medicas="piel sensible",
            )
            db.session.add(mascota)
            db.session.flush()
            db.session.add(MascotaDueno(mascota_id=mascota.id, cliente_id=cliente.id, es_principal=True))
            db.session.flush()

        cita = Cita.query.filter_by(fecha_hora_inicio=datetime(2025, 6, 3, 9, 0)).first()
        if not cita:
            cita = Cita(
                mascota_id=mascota.id,
                groomer_id=groomer.id,
                servicio_id=servicio.id,
                fecha_hora_inicio=datetime(2025, 6, 3, 9, 0),
                fecha_hora_fin=datetime(2025, 6, 3, 10, 30),
                duracion_estimada=90,
                estado="agendada",
                notas="Cita del módulo 6.2",
                creado_por=cliente.usuario_id,
            )
            db.session.add(cita)
            db.session.flush()

        ficha = FichaGrooming.query.filter_by(cita_id=cita.id).first()
        if not ficha:
            ficha = FichaGrooming(
                cita_id=cita.id,
                groomer_id=groomer.id,
                estado_inicial="Llega con nudos leves",
                temperatura_ingreso=37.5,
                peso_momento_servicio=4.2,
                raza_tamano_momento="poodle pequeno",
                notas_internas="Revisar orejas",
                checklist_completo=False,
            )
            db.session.add(ficha)
            db.session.flush()

        item_obs = ChecklistItemTemplate.query.filter_by(servicio_id=servicio.id, nombre="Revisión de orejas").first()
        if not item_obs:
            item_obs = ChecklistItemTemplate(
                servicio_id=servicio.id,
                nombre="Revisión de orejas",
                requiere_obs=True,
                orden=1,
                activo=True,
            )
            db.session.add(item_obs)
            db.session.flush()

        item_simple = ChecklistItemTemplate.query.filter_by(servicio_id=servicio.id, nombre="Cepillado final").first()
        if not item_simple:
            item_simple = ChecklistItemTemplate(
                servicio_id=servicio.id,
                nombre="Cepillado final",
                requiere_obs=False,
                orden=2,
                activo=True,
            )
            db.session.add(item_simple)
            db.session.flush()

        if not FichaChecklist.query.filter_by(ficha_id=ficha.id, item_id=item_obs.id).first():
            db.session.add(FichaChecklist(ficha_id=ficha.id, item_id=item_obs.id, completado=False))
        if not FichaChecklist.query.filter_by(ficha_id=ficha.id, item_id=item_simple.id).first():
            db.session.add(FichaChecklist(ficha_id=ficha.id, item_id=item_simple.id, completado=False))

        producto = Producto.query.filter_by(sku="JAB-62").first()
        if not producto:
            producto = Producto(
                nombre="Jabon neutro 62",
                sku="JAB-62",
                precio_base=12.5,
                stock=10,
                stock_minimo=2,
                activo=True,
            )
            db.session.add(producto)

        db.session.commit()
        return {
            "cita_id": cita.id,
            "ficha_id": ficha.id,
            "item_obs_id": item_obs.id,
            "item_simple_id": item_simple.id,
            "producto_id": producto.id,
            "groomer_id": groomer.id,
        }


def test_ficha_por_cita_y_actualizacion_base(client, token_groomer, modulo_62_seed):
    r = client.get(f"/api/fichas/cita/{modulo_62_seed['cita_id']}", headers=_auth(token_groomer))
    assert r.status_code == 200
    payload = r.get_json()
    data = payload.get("data", payload)
    assert data["ficha"]["id"] == modulo_62_seed["ficha_id"]
    assert data["ficha"]["cita"]["id"] == modulo_62_seed["cita_id"]

    update = client.patch(
        f"/api/fichas/{modulo_62_seed['ficha_id']}",
        json={
            "estado_inicial": "Se actualiza el estado inicial",
            "temperatura_ingreso": 38.1,
            "peso_momento_servicio": 4.4,
            "raza_tamano_momento": "poodle mini",
            "notas_internas": "Nueva nota",
        },
        headers=_auth(token_groomer),
    )
    assert update.status_code == 200
    update_payload = update.get_json()
    update_data = update_payload.get("data", update_payload)
    assert update_data["ficha"]["estado_inicial"] == "Se actualiza el estado inicial"
    assert float(update_data["ficha"]["temperatura_ingreso"]) == pytest.approx(38.1)


def test_ficha_checklist_fotos_insumos_y_cierre(client, token_groomer, modulo_62_seed):
    invalid_check = client.patch(
        f"/api/fichas/{modulo_62_seed['ficha_id']}/checklist/{modulo_62_seed['item_obs_id']}",
        json={"completado": True},
        headers=_auth(token_groomer),
    )
    assert invalid_check.status_code == 422

    ok_check = client.patch(
        f"/api/fichas/{modulo_62_seed['ficha_id']}/checklist/{modulo_62_seed['item_obs_id']}",
        json={"completado": True, "observacion": "Orejas limpias"},
        headers=_auth(token_groomer),
    )
    assert ok_check.status_code == 200
    ok_check_payload = ok_check.get_json()
    ok_check_data = ok_check_payload.get("data", ok_check_payload)
    assert ok_check_data["items_pendientes"] == 1
    assert ok_check_data["checklist_completo"] is False

    ok_check_2 = client.patch(
        f"/api/fichas/{modulo_62_seed['ficha_id']}/checklist/{modulo_62_seed['item_simple_id']}",
        json={"completado": True},
        headers=_auth(token_groomer),
    )
    assert ok_check_2.status_code == 200
    ok_check_2_payload = ok_check_2.get_json()
    ok_check_2_data = ok_check_2_payload.get("data", ok_check_2_payload)
    assert ok_check_2_data["items_pendientes"] == 0
    assert ok_check_2_data["checklist_completo"] is True

    before_photo = client.post(
        f"/api/fichas/{modulo_62_seed['ficha_id']}/fotos",
        data={
            "archivo": (BytesIO(b"before-photo"), "antes.jpg"),
            "tipo": "antes",
            "descripcion": "Foto inicial",
        },
        content_type="multipart/form-data",
        headers=_auth(token_groomer),
    )
    assert before_photo.status_code == 201

    after_photo = client.post(
        f"/api/fichas/{modulo_62_seed['ficha_id']}/fotos",
        data={
            "archivo": (BytesIO(b"after-photo"), "despues.jpg"),
            "tipo": "despues",
            "descripcion": "Foto final",
        },
        content_type="multipart/form-data",
        headers=_auth(token_groomer),
    )
    assert after_photo.status_code == 201

    invalid_insumos = client.patch(
        f"/api/fichas/{modulo_62_seed['ficha_id']}/insumos",
        json={"insumos": [{"producto_id": modulo_62_seed['producto_id'], "cantidad": -1}]},
        headers=_auth(token_groomer),
    )
    assert invalid_insumos.status_code == 422

    insumos = client.patch(
        f"/api/fichas/{modulo_62_seed['ficha_id']}/insumos",
        json={"insumos": [{"producto_id": modulo_62_seed['producto_id'], "cantidad": 1, "devuelto": 0, "desperdicio": 0}]},
        headers=_auth(token_groomer),
    )
    assert insumos.status_code == 200

    cierre = client.patch(
        f"/api/fichas/{modulo_62_seed['ficha_id']}/cerrar",
        json={
            "estado_final": "Mascota entregada sin incidencias",
            "observaciones_final": "Lista para retiro",
            "duracion_real": 95,
        },
        headers=_auth(token_groomer),
    )
    assert cierre.status_code == 200
    cierre_payload = cierre.get_json()
    cierre_data = cierre_payload.get("data", cierre_payload)
    assert cierre_data["ok"] is True


def test_ficha_por_cita_inexistente_devuelve_404(client, token_groomer):
    r = client.get("/api/fichas/cita/999999", headers=_auth(token_groomer))
    assert r.status_code == 404