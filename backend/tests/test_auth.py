import os

import pytest

from app import create_app
from app.extensions import db
from app.routes import auth as auth_routes
from app.services import auth_service


class FakeRol:
    def __init__(self, nombre="Administrador", nivel_acceso="full"):
        self.nombre = nombre
        self.nivel_acceso = nivel_acceso


class FakeUser:
    def __init__(self, with_2fa=False):
        self.id = "user-id"
        self.email = "test@spa.com"
        self.activo = True
        self.token_2fa = "secret" if with_2fa else None
        self.rol = FakeRol()
        self.perfil_empleado = None
        self.perfil_cliente = None

    def check_password(self, _password):
        return True

    def tiene_2fa(self):
        return self.token_2fa is not None

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "rol": self.rol.nombre,
            "nivel_acceso": self.rol.nivel_acceso,
            "nombre_completo": "Admin Spa"
        }


@pytest.fixture()
def app():
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-spa-mascotas-min32chars"
    app = create_app()
    app.config.update(TESTING=True)
    return app


@pytest.fixture()
def client(app):
    return app.test_client()


def test_login_success_no_2fa(client, monkeypatch):
    fake_user = FakeUser(with_2fa=False)

    monkeypatch.setattr(auth_service, "is_blocked", lambda _email: False)
    monkeypatch.setattr(auth_service, "get_usuario_by_email", lambda _email: fake_user)
    monkeypatch.setattr(auth_service, "log_audit", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(auth_service, "generate_tokens", lambda _u: ("a", "r"))
    monkeypatch.setattr(db.session, "commit", lambda: None)

    response = client.post("/api/auth/login", json={"email": fake_user.email, "password": "x"})
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["data"]["access_token"] == "a"
    assert payload["data"]["refresh_token"] == "r"


def test_login_requires_2fa(client, monkeypatch):
    fake_user = FakeUser(with_2fa=True)

    monkeypatch.setattr(auth_service, "is_blocked", lambda _email: False)
    monkeypatch.setattr(auth_service, "get_usuario_by_email", lambda _email: fake_user)
    monkeypatch.setattr(auth_service, "log_audit", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(auth_service, "generate_temp_token", lambda _u: "temp")

    response = client.post("/api/auth/login", json={"email": fake_user.email, "password": "x"})
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["data"]["requiere_2fa"] is True
    assert payload["data"]["temp_token"] == "temp"


def test_verificar_2fa_ok(client, monkeypatch):
    fake_user = FakeUser(with_2fa=True)

    class QueryStub:
        def filter_by(self, **_kwargs):
            return self

        def first(self):
            return fake_user

    monkeypatch.setattr(auth_routes, "decode_token", lambda _t: {"sub": "user-id", "tipo": "pre_2fa"})
    monkeypatch.setattr(auth_routes.Usuario, "query", QueryStub())
    monkeypatch.setattr(auth_service, "verificar_2fa", lambda _u, _c: True)
    monkeypatch.setattr(auth_service, "generate_tokens", lambda _u: ("a", "r"))
    monkeypatch.setattr(auth_service, "log_audit", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(db.session, "commit", lambda: None)

    response = client.post(
        "/api/auth/verificar-2fa",
        json={"temp_token": "temp", "codigo_totp": "123456"}
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["data"]["access_token"] == "a"


def test_refresh_ok(client, monkeypatch):
    fake_user = FakeUser(with_2fa=False)

    class QueryStub:
        def filter_by(self, **_kwargs):
            return self

        def first(self):
            return fake_user

    monkeypatch.setattr(auth_routes, "decode_token", lambda _t: {"sub": "user-id"})
    monkeypatch.setattr(auth_routes.Usuario, "query", QueryStub())

    response = client.post(
        "/api/auth/refresh",
        headers={"Authorization": "Bearer refresh"}
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert "access_token" in payload["data"]
