import importlib

import pyotp
import pytest


@pytest.fixture(autouse=True)
def restaurar_auth_service():
    from app.services import auth_service

    importlib.reload(auth_service)
    yield
    importlib.reload(auth_service)


def test_login_credenciales_invalidas(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "noexiste@test.com", "password": "wrong"},
    )
    assert response.status_code == 401


def test_login_exitoso_retorna_token(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "admin@test.com", "password": "pass"},
    )
    assert response.status_code == 200
    payload = response.get_json()["data"]
    assert "access_token" in payload
    assert "refresh_token" in payload
    assert payload["usuario"]["rol"] == "Admin"


def test_login_retorna_rol_correcto(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "groomer@test.com", "password": "pass"},
    )
    assert response.status_code == 200
    assert response.get_json()["data"]["usuario"]["rol"] == "Groomer"


def test_refresh_token_funciona(client):
    login = client.post(
        "/api/auth/login",
        json={"email": "admin@test.com", "password": "pass"},
    )
    refresh_token = login.get_json()["data"]["refresh_token"]
    response = client.post(
        "/api/auth/refresh",
        headers={"Authorization": f"Bearer {refresh_token}"},
    )
    assert response.status_code == 200
    assert "access_token" in response.get_json()["data"]


def test_logout_invalida_token(client):
    login = client.post(
        "/api/auth/login",
        json={"email": "admin@test.com", "password": "pass"},
    )
    data = login.get_json()["data"]
    access_token = data["access_token"]
    refresh_token = data["refresh_token"]

    response = client.post(
        "/api/auth/logout",
        json={"refresh_token": refresh_token},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 200

    response_after = client.get("/api/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert response_after.status_code == 401


def test_me_retorna_usuario(client):
    login = client.post(
        "/api/auth/login",
        json={"email": "admin@test.com", "password": "pass"},
    )
    access_token = login.get_json()["data"]["access_token"]
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    assert response.get_json()["data"]["rol"] == "Admin"


def test_login_fallido_registra_audit_log(client):
    from app.models import AuditLog

    with client.application.app_context():
        before = AuditLog.query.count()

    response = client.post(
        "/api/auth/login",
        json={"email": "fallo@test.com", "password": "bad"},
    )
    assert response.status_code == 401

    with client.application.app_context():
        after = AuditLog.query.count()
        ultimo = AuditLog.query.order_by(AuditLog.id.desc()).first()

    assert after == before + 1
    assert ultimo.datos_despues["action"] == "login_fail"
    assert ultimo.datos_despues["email"] == "fallo@test.com"


def test_bloqueo_por_cinco_intentos_en_15_min(client):
    email = "bloqueo@test.com"
    for _ in range(5):
        response = client.post(
            "/api/auth/login",
            json={"email": email, "password": "wrong"},
        )
        assert response.status_code == 401

    bloqueado = client.post(
        "/api/auth/login",
        json={"email": email, "password": "wrong"},
    )
    assert bloqueado.status_code == 429


def test_groomer_no_accede_reportes_financieros(client, token_groomer):
    for url in [
        "/api/reportes/dashboard",
        "/api/cobros/cierre-caja",
        "/api/reportes/top-servicios",
    ]:
        response = client.get(url, headers=auth(token_groomer))
        assert response.status_code == 403


def test_cliente_no_ve_ventas_admin(client, token_cliente):
    for url in [
        "/api/reportes/dashboard",
        "/api/cobros/cierre-caja",
        "/api/alertas/inventario",
    ]:
        response = client.get(url, headers=auth(token_cliente))
        assert response.status_code == 403


def test_groomer_no_crea_citas(client, token_groomer):
    response = client.post(
        "/api/citas",
        json={"mascota_id": 1, "groomer_id": 1, "servicio_id": 1, "fecha_hora_inicio": "2099-01-01T10:00"},
        headers=auth(token_groomer),
    )
    assert response.status_code == 403


def test_cliente_no_confirma_citas(client, token_cliente):
    response = client.patch("/api/citas/1/confirmar", headers=auth(token_cliente))
    assert response.status_code == 403


def test_recepcion_no_gestiona_usuarios(client, token_recep):
    response = client.post(
        "/api/usuarios",
        json={"email": "nuevo@test.com", "password": "pass1234", "rol_nombre": "Cliente"},
        headers=auth(token_recep),
    )
    assert response.status_code == 403


def test_admin_crea_usuario(client, token_admin):
    response = client.post(
        "/api/usuarios",
        json={
            "email": "nuevo_test@test.com",
            "password": "password123",
            "rol_nombre": "Cliente",
            "nombre": "Nuevo Test",
        },
        headers=auth(token_admin),
    )
    assert response.status_code in (200, 201)


def test_endpoint_sin_token_retorna_401(client):
    for url in ["/api/citas", "/api/carrito/me", "/api/groomers/me/agenda"]:
        response = client.get(url)
        assert response.status_code == 401


def test_token_invalido_retorna_401(client):
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer token_falso_invalido"},
    )
    assert response.status_code == 422


def test_2fa_setup_requiere_admin_o_recepcion(client, token_cliente):
    response = client.post("/api/auth/setup-2fa", headers=auth(token_cliente))
    assert response.status_code == 403


def test_setup_y_verificacion_2fa_admin(client, token_admin):
    setup = client.post("/api/auth/setup-2fa", headers=auth(token_admin))
    assert setup.status_code == 200
    data = setup.get_json()["data"]
    secret = data["secret"]
    code = pyotp.TOTP(secret).now()

    verify = client.post(
        "/api/auth/verify-2fa",
        json={"code": code},
        headers=auth(token_admin),
    )
    assert verify.status_code == 200


def test_gestion_usuarios_requiere_admin(client, token_recep):
    response = client.get("/api/usuarios", headers=auth(token_recep))
    assert response.status_code == 403


def test_password_hasheada_en_db(client, token_admin):
    email = "hashtest@test.com"
    response = client.post(
        "/api/usuarios",
        json={"email": email, "password": "mi_pass_123", "rol_nombre": "Cliente"},
        headers=auth(token_admin),
    )
    assert response.status_code in (200, 201)

    from app.models.usuario import Usuario

    with client.application.app_context():
        usuario = Usuario.query.filter_by(email=email).first()

    assert usuario.password_hash != "mi_pass_123"
    assert usuario.password_hash.startswith("pbkdf2:")


def auth(token):
    return {"Authorization": f"Bearer {token}"}