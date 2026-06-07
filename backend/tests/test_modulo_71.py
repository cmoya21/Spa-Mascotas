from datetime import datetime

import pytest

from tests.conftest import auth


@pytest.fixture(scope="session")
def modulo_71_seed(app):
    with app.app_context():
        from app.extensions import db
        from app.models.agenda import Cita, Servicio
        from app.models.grooming import FichaGrooming
        from app.models.inventario import Producto
        from app.models.usuario import Groomer, Usuario

        groomer = Groomer.query.join(Usuario).filter(Usuario.email == "groomer@test.com").first()
        servicio = Servicio.query.first()
        cita = Cita.query.filter_by(groomer_id=groomer.id).first() if groomer else None

        if not groomer or not servicio or not cita:
            raise RuntimeError("Faltan datos base para sembrar módulo 7.1")

        ficha = FichaGrooming.query.filter_by(cita_id=cita.id).first()
        if not ficha:
            ficha = FichaGrooming(
                cita_id=cita.id,
                groomer_id=groomer.id,
                estado_inicial="Preparacion modulo 7.1",
                checklist_completo=False,
            )
            db.session.add(ficha)
            db.session.flush()

        producto = Producto.query.filter_by(sku="MOD71-INS").first()
        if not producto:
            producto = Producto(
                nombre="Shampoo modulo 7.1",
                sku="MOD71-INS",
                precio_base=10,
                stock=30,
                stock_minimo=3,
                activo=True,
            )
            db.session.add(producto)
            db.session.flush()

        servicio.consumo_insumos = [
            {
                "producto_id": producto.id,
                "cantidad": 2,
            }
        ]

        db.session.commit()
        return {
            "ficha_id": ficha.id,
            "groomer_id": groomer.id,
            "servicio_id": servicio.id,
            "producto_id": producto.id,
        }


def test_registrar_salida_insumos_ok(client, token_groomer, modulo_71_seed):
    r = client.post(
        "/api/insumos/salida",
        json={
            "ficha_id": modulo_71_seed["ficha_id"],
            "insumos": [
                {
                    "producto_id": modulo_71_seed["producto_id"],
                    "cantidad_entregada": 2,
                    "notas": "Salida antes del servicio",
                }
            ],
        },
        headers=auth(token_groomer),
    )
    assert r.status_code == 201
    payload = r.get_json()
    assert payload["registros_creados"] >= 1
    assert payload["insumos"][0]["producto_id"] == modulo_71_seed["producto_id"]


def test_registrar_salida_insumos_ficha_cerrada_rechaza(client, token_groomer, modulo_71_seed):
    from app.extensions import db
    from app.models.grooming import FichaGrooming

    with client.application.app_context():
        ficha = FichaGrooming.query.get(modulo_71_seed["ficha_id"])
        ficha.fecha_cierre = datetime.utcnow()
        db.session.commit()

    r = client.post(
        "/api/insumos/salida",
        json={
            "ficha_id": modulo_71_seed["ficha_id"],
            "insumos": [
                {
                    "producto_id": modulo_71_seed["producto_id"],
                    "cantidad_entregada": 1,
                }
            ],
        },
        headers=auth(token_groomer),
    )
    assert r.status_code == 409

    with client.application.app_context():
        ficha = FichaGrooming.query.get(modulo_71_seed["ficha_id"])
        ficha.fecha_cierre = None
        db.session.commit()


def test_productos_disponibles_para_insumos_devuelve_sugeridos(client, token_groomer, modulo_71_seed):
    r = client.get(
        "/api/productos/disponibles-para-insumos",
        query_string={"servicio_id": modulo_71_seed["servicio_id"]},
        headers=auth(token_groomer),
    )
    assert r.status_code == 200
    data = r.get_json()
    assert isinstance(data, list)
    item = next((x for x in data if x["id"] == modulo_71_seed["producto_id"]), None)
    assert item is not None
    assert item["es_sugerido"] is True


def test_log_groomer_y_log_admin(client, token_groomer, token_recep, modulo_71_seed):
    registrar = client.post(
        "/api/insumos/salida",
        json={
            "ficha_id": modulo_71_seed["ficha_id"],
            "insumos": [
                {
                    "producto_id": modulo_71_seed["producto_id"],
                    "cantidad_entregada": 1,
                    "notas": "Registro para logs",
                }
            ],
        },
        headers=auth(token_groomer),
    )
    assert registrar.status_code in (201, 409)

    r_groomer = client.get("/api/insumos/log-groomer", headers=auth(token_groomer))
    assert r_groomer.status_code == 200
    data_groomer = r_groomer.get_json()
    assert isinstance(data_groomer, list)

    r_admin = client.get("/api/insumos/log-admin", headers=auth(token_recep))
    assert r_admin.status_code == 200
    data_admin = r_admin.get_json()
    assert isinstance(data_admin, list)


def test_audit_log_registra_groomer_en_salida(client, token_groomer, modulo_71_seed):
    from app.models.usuario import AuditLog

    r = client.post(
        "/api/insumos/salida",
        json={
            "ficha_id": modulo_71_seed["ficha_id"],
            "insumos": [
                {
                    "producto_id": modulo_71_seed["producto_id"],
                    "cantidad_entregada": 1,
                }
            ],
        },
        headers=auth(token_groomer),
    )
    assert r.status_code == 201

    with client.application.app_context():
        log = (
            AuditLog.query.filter_by(tabla="salida_insumos")
            .order_by(AuditLog.id.desc())
            .first()
        )
        assert log is not None
        assert log.groomer_id == modulo_71_seed["groomer_id"]
        assert (log.datos_despues or {}).get("groomer_id") == modulo_71_seed["groomer_id"]
