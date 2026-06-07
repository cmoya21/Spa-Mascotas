import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from flask_jwt_extended import create_access_token
from sqlalchemy import Integer, JSON, String


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def _login_token(client, email, password="pass"):
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    payload = response.get_json() or {}
    data = payload.get("data", payload)
    return data["access_token"]


def _sembrar_datos_base(db):
    from app.models.agenda import Cita, Servicio
    from app.models.mascota import Mascota, MascotaDueno
    from app.models.rol import Rol
    from app.models.usuario import Cliente, Groomer, Usuario

    roles = {nombre: Rol(nombre=nombre, permisos={}) for nombre in ["Admin", "Recepcion", "Groomer", "Cliente"]}
    for rol in roles.values():
        db.session.add(rol)
    db.session.flush()

    u_admin = Usuario(
        email="admin@test.com",
        rol_id=roles["Admin"].id,
        estado_activo=True,
    )
    u_recep = Usuario(
        email="recep@test.com",
        rol_id=roles["Recepcion"].id,
        estado_activo=True,
    )
    u_groo = Usuario(
        email="groomer@test.com",
        rol_id=roles["Groomer"].id,
        estado_activo=True,
    )
    u_cli = Usuario(
        email="cliente@test.com",
        rol_id=roles["Cliente"].id,
        estado_activo=True,
    )
    for usuario in [u_admin, u_recep, u_groo, u_cli]:
        usuario.set_password("pass")
    for usuario in [u_admin, u_recep, u_groo, u_cli]:
        db.session.add(usuario)
    db.session.flush()

    groomer = Groomer(
        usuario_id=u_groo.id,
        nombre="Ana Test",
        apellido="Groomer",
        capacidad_simultanea=1,
        estado_activo=True,
    )
    cliente = Cliente(
        usuario_id=u_cli.id,
        nombre="María Test",
        apellido="Cliente",
        telefono="591-70000000",
        canal_notificacion="whatsapp",
    )
    db.session.add(groomer)
    db.session.add(cliente)
    db.session.flush()

    mascota = Mascota(
        nombre="Luna",
        especie="perro",
        raza="Poodle",
        peso_kg=4.2,
        temperamento="tranquilo",
    )
    db.session.add(mascota)
    db.session.flush()

    db.session.add(
        MascotaDueno(
            mascota_id=mascota.id,
            cliente_id=cliente.id,
            es_principal=True,
        )
    )

    servicio = Servicio(
        nombre="Baño completo",
        duracion_base_minutos=60,
        precio_base=80.0,
        activo=True,
        factor_tamano_raza={"pequeno": 1.0, "mediano": 1.15, "grande": 1.3, "gigante": 1.3},
    )
    db.session.add(servicio)
    db.session.flush()

    cita = Cita(
        mascota_id=mascota.id,
        groomer_id=groomer.id,
        servicio_id=servicio.id,
        fecha_hora_inicio=datetime(2099, 1, 6, 9, 0, 0),
        fecha_hora_fin=datetime(2099, 1, 6, 10, 0, 0),
        duracion_estimada=60,
        precio_estimado=80.0,
        estado="agendada",
        creado_por=u_recep.id,
    )
    db.session.add(cita)
    db.session.commit()


def _adaptar_modelos_para_sqlite(db):
    for table in db.metadata.tables.values():
        for column in table.columns:
            type_name = column.type.__class__.__name__.lower()
            if type_name == "jsonb":
                column.type = JSON()
                if column.server_default is not None and "::jsonb" in str(column.server_default.arg).lower():
                    column.server_default = None
            elif type_name == "bigint":
                column.type = Integer()
            elif type_name == "inet":
                column.type = String(45)
            elif type_name == "uuid":
                column.type = String(36)


@pytest.fixture(scope="session")
def app():
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-spa-mascotas-min32chars"
    os.environ["SECRET_KEY"] = "test-secret"
    from app import create_app
    from app.extensions import db as _db
    from app.services import auth_service as _auth_service

    app = create_app()
    app.config.update(TESTING=True)

    with app.app_context():
        _auth_service.is_blocked = lambda _email: False
        _auth_service.log_audit = lambda *args, **kwargs: None
        _adaptar_modelos_para_sqlite(_db)
        _db.create_all()
        _sembrar_datos_base(_db)
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def token_admin(client):
    with client.application.app_context():
        return create_access_token(identity="1", additional_claims={"rol": "Admin"})


@pytest.fixture()
def token_recep(client):
    return _login_token(client, "recep@test.com")


@pytest.fixture()
def token_groomer(client):
    return _login_token(client, "groomer@test.com")


@pytest.fixture()
def token_cliente(client):
    return _login_token(client, "cliente@test.com")


def auth(token):
    return {"Authorization": f"Bearer {token}"}
