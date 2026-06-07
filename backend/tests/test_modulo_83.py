from datetime import datetime

from tests.conftest import auth


def test_listar_promociones_publico(client):
    r = client.get("/api/promociones")
    assert r.status_code == 200
    assert isinstance(r.json, list)


def test_crear_promocion_admin(client, token_admin):
    r = client.post(
        "/api/promociones",
        json={"nombre": "Test 20%", "tipo": "porcentaje", "valor": 20, "codigo_cupon": "TEST20"},
        headers=auth(token_admin),
    )
    assert r.status_code in (200, 201)


def test_porcentaje_mayor_100_rechazado(client, token_admin):
    r = client.post(
        "/api/promociones",
        json={"nombre": "Invalida", "tipo": "porcentaje", "valor": 150},
        headers=auth(token_admin),
    )
    assert r.status_code == 422


def test_cupon_duplicado_rechazado(client, token_admin):
    client.post(
        "/api/promociones",
        json={"nombre": "P1", "tipo": "porcentaje", "valor": 10, "codigo_cupon": "DUP99"},
        headers=auth(token_admin),
    )
    r = client.post(
        "/api/promociones",
        json={"nombre": "P2", "tipo": "porcentaje", "valor": 10, "codigo_cupon": "DUP99"},
        headers=auth(token_admin),
    )
    assert r.status_code == 422


def test_validar_cupon_valido(client, token_admin):
    client.post(
        "/api/promociones",
        json={"nombre": "ValidTest", "tipo": "porcentaje", "valor": 20, "codigo_cupon": "VALID20", "activa": True},
        headers=auth(token_admin),
    )
    r = client.post(
        "/api/promociones/validar-cupon",
        json={"codigo_cupon": "VALID20", "subtotal": 100.0},
    )
    assert r.status_code == 200
    data = r.json
    assert data["descuento_calculado"] == 20.0
    assert data["total_con_descuento"] == 80.0


def test_cupon_invalido_retorna_404(client):
    r = client.post(
        "/api/promociones/validar-cupon",
        json={"codigo_cupon": "NOEXISTE", "subtotal": 100.0},
    )
    assert r.status_code == 404


def test_beneficios_frecuente_requiere_auth(client):
    r = client.get("/api/clientes/me/beneficios-frecuente")
    assert r.status_code == 401


def test_beneficios_frecuente_cliente(client, token_cliente):
    r = client.get("/api/clientes/me/beneficios-frecuente", headers=auth(token_cliente))
    assert r.status_code == 200
    assert "total_visitas" in r.json
    assert "nivel" in r.json
    assert "descuento_disponible" in r.json


def test_beneficios_frecuente_bronze(client, token_cliente):
    from app.extensions import db
    from app.models.agenda import Cita, Servicio
    from app.models.mascota import Mascota
    from app.models.usuario import Cliente, Groomer, Usuario

    with client.application.app_context():
        cliente = Cliente.query.join(Usuario).filter(Usuario.email == "cliente@test.com").first()
        groomer = Groomer.query.join(Usuario).filter(Usuario.email == "groomer@test.com").first()
        servicio = Servicio.query.first()
        mascota = Mascota.query.first()
        base_cita = Cita.query.first()

        if not cliente or not groomer or not servicio or not mascota or not base_cita:
            raise RuntimeError("Faltan datos base para probar beneficios frecuentes")

        base_cita.estado = "completada"
        db.session.add(
            Cita(
                mascota_id=mascota.id,
                groomer_id=groomer.id,
                servicio_id=servicio.id,
                fecha_hora_inicio=datetime(2099, 2, 1, 9, 0, 0),
                fecha_hora_fin=datetime(2099, 2, 1, 10, 0, 0),
                duracion_estimada=60,
                precio_estimado=80.0,
                estado="completada",
                creado_por=cliente.usuario_id,
            )
        )
        db.session.add(
            Cita(
                mascota_id=mascota.id,
                groomer_id=groomer.id,
                servicio_id=servicio.id,
                fecha_hora_inicio=datetime(2099, 2, 2, 9, 0, 0),
                fecha_hora_fin=datetime(2099, 2, 2, 10, 0, 0),
                duracion_estimada=60,
                precio_estimado=80.0,
                estado="completada",
                creado_por=cliente.usuario_id,
            )
        )
        db.session.commit()

    r = client.get("/api/clientes/me/beneficios-frecuente", headers=auth(token_cliente))
    assert r.status_code == 200
    assert r.json["total_visitas"] >= 3
    assert r.json["nivel"] == "Bronze"
    assert r.json["descuento_disponible"] == 5


def test_toggle_promocion(client, token_admin):
    r_create = client.post(
        "/api/promociones",
        json={"nombre": "Toggle", "tipo": "monto_fijo", "valor": 10},
        headers=auth(token_admin),
    )
    assert r_create.status_code in (200, 201)
    pid = r_create.get_json()["id"] if isinstance(r_create.get_json(), dict) else r_create.json["id"]
    r = client.patch(f"/api/promociones/{pid}/toggle", headers=auth(token_admin))
    assert r.status_code == 200


def test_aplicar_promocion_a_factura_actualiza_total(client, token_admin, token_recep):
    from app.extensions import db
    from app.models.agenda import Cita, Servicio
    from app.models.facturacion import Factura
    from app.models.mascota import Mascota
    from app.models.usuario import Cliente, Groomer, Usuario

    factura_id = None

    with client.application.app_context():
        cliente = Cliente.query.join(Usuario).filter(Usuario.email == "cliente@test.com").first()
        groomer = Groomer.query.join(Usuario).filter(Usuario.email == "groomer@test.com").first()
        servicio = Servicio.query.first()
        mascota = Mascota.query.first()
        cita = Cita.query.first()
        if not cliente or not groomer or not servicio or not mascota or not cita:
            raise RuntimeError("Faltan datos base para factura promocional")

        cita.estado = "completada"
        db.session.commit()

        factura = Factura(
            numero="FAC-TEST-0001",
            cita_id=cita.id,
            cliente_id=cliente.id,
            subtotal=80.0,
            impuesto=0,
            descuento=0,
            total=80.0,
            estado="pendiente",
            metodo_pago="efectivo",
        )
        db.session.add(factura)
        db.session.commit()
        factura_id = factura.id

    promo = client.post(
        "/api/promociones",
        json={"nombre": "Factura 10", "tipo": "monto_fijo", "valor": 10, "codigo_cupon": "FACT10", "activa": True},
        headers=auth(token_admin),
    )
    assert promo.status_code in (200, 201)
    promo_id = promo.get_json()["id"]

    r = client.post(
        f"/api/promociones/{promo_id}/aplicar-a-factura",
        json={"factura_id": factura_id},
        headers=auth(token_recep),
    )
    assert r.status_code in (200, 201)
    data = r.get_json()
    assert data["descuento"] == 10.0
    assert data["total"] == 70.0

