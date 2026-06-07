import os
from datetime import datetime, timedelta, timezone

import pytest
from flask_jwt_extended import create_access_token

from app import create_app
from app.extensions import db
from app.models import (
    ChecklistItemTemplate,
    Cita,
    Cliente,
    FichaChecklist,
    FichaGrooming,
    FotoFicha,
    Groomer,
    Mascota,
    Producto,
    Rol,
    Servicio,
    Usuario,
)


@pytest.fixture()
def app():
    app = create_app()
    app.config.update(TESTING=True)
    return app


@pytest.fixture()
def client(app):
    return app.test_client()


def _skip_if_not_enabled(app):
    if os.getenv("RUN_DB_TESTS") != "1":
        pytest.skip("RUN_DB_TESTS no esta habilitado")
    if not app.config.get("SQLALCHEMY_DATABASE_URI", "").startswith("postgres"):
        pytest.skip("Solo para PostgreSQL con triggers habilitados")


def test_cerrar_ficha_descuenta_stock(app, client):
    _skip_if_not_enabled(app)

    with app.app_context():
        suffix = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")

        created_rol = False
        created_rol_cliente = False

        rol = Rol.query.filter_by(nombre="Groomer").first()
        if not rol:
            rol = Rol(nombre="Groomer")
            db.session.add(rol)
            db.session.flush()
            created_rol = True

        rol_cliente = Rol.query.filter_by(nombre="Cliente").first()
        if not rol_cliente:
            rol_cliente = Rol(nombre="Cliente")
            db.session.add(rol_cliente)
            db.session.flush()
            created_rol_cliente = True

        usuario = Usuario(email=f"groomer_test_{suffix}@spa.local", rol_id=rol.id, estado_activo=True)
        usuario.set_password("Test1234!")
        db.session.add(usuario)
        db.session.flush()

        groomer = Groomer(usuario_id=usuario.id, nombre="Test", apellido="Groomer")
        db.session.add(groomer)

        cliente_user = Usuario(email=f"cliente_test_{suffix}@spa.local", rol_id=rol_cliente.id, estado_activo=True)
        cliente_user.set_password("Test1234!")
        db.session.add(cliente_user)
        db.session.flush()

        cliente = Cliente(usuario_id=cliente_user.id, nombre="Cliente", apellido="Test")
        db.session.add(cliente)

        mascota = Mascota(nombre="Bobby", especie="Perro")
        db.session.add(mascota)

        servicio = Servicio(
            nombre=f"Bano {suffix}",
            precio_base=20,
            duracion_base_minutos=30,
            activo=True,
        )
        db.session.add(servicio)
        db.session.flush()

        cita = Cita(
            mascota_id=mascota.id,
            groomer_id=groomer.id,
            servicio_id=servicio.id,
            fecha_hora_inicio=datetime.now(timezone.utc),
            fecha_hora_fin=datetime.now(timezone.utc) + timedelta(minutes=30),
            duracion_estimada=30,
        )
        db.session.add(cita)
        db.session.flush()

        ficha = FichaGrooming(cita_id=cita.id, groomer_id=groomer.id)
        ficha.insumos_consumidos = [{"producto_id": 1, "cantidad": 2}]
        db.session.add(ficha)
        db.session.flush()

        template = ChecklistItemTemplate(servicio_id=servicio.id, nombre="Bano", activo=True)
        db.session.add(template)
        db.session.flush()

        checklist = FichaChecklist(
            ficha_id=ficha.id,
            item_id=template.id,
            completado=True,
            completado_en=datetime.now(timezone.utc),
        )
        db.session.add(checklist)

        foto_antes = FotoFicha(ficha_id=ficha.id, url="https://img/antes.jpg", tipo="antes")
        foto_despues = FotoFicha(ficha_id=ficha.id, url="https://img/despues.jpg", tipo="despues")
        db.session.add(foto_antes)
        db.session.add(foto_despues)

        producto = Producto(nombre=f"Shampoo {suffix}", stock=10, stock_minimo=1)
        db.session.add(producto)
        db.session.commit()

        ficha.insumos_consumidos = [{"producto_id": producto.id, "cantidad": 2}]
        db.session.commit()

        token = create_access_token(identity=str(usuario.id), additional_claims={"rol": "Groomer"})

        response = client.patch(
            f"/api/grooming/fichas/{ficha.id}/cerrar",
            json={"estado_final": "Ok"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200

        db.session.refresh(producto)
        assert producto.stock == 8

        db.session.delete(foto_antes)
        db.session.delete(foto_despues)
        db.session.delete(checklist)
        db.session.delete(template)
        db.session.delete(ficha)
        db.session.delete(cita)
        db.session.delete(servicio)
        db.session.delete(mascota)
        db.session.delete(cliente)
        db.session.delete(cliente_user)
        db.session.delete(groomer)
        db.session.delete(usuario)
        if created_rol and rol and rol.id:
            db.session.delete(rol)
        if created_rol_cliente and rol_cliente and rol_cliente.id:
            db.session.delete(rol_cliente)
        db.session.delete(producto)
        db.session.commit()
