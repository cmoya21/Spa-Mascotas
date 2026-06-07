from datetime import datetime, timedelta, time, timezone


def test_cliente_gestiona_multiples_mascotas_y_desvincula_sin_borrar(client, token_cliente):
    from app.extensions import db
    from app.models import Cliente, Mascota, MascotaDueno, Rol, Usuario

    cliente = Cliente.query.join(Usuario).filter(Usuario.email == "cliente@test.com").first()
    rol_cliente = Rol.query.filter_by(nombre="Cliente").first()
    mascota_extra = Mascota(nombre="Kira", especie="perro", raza="Labrador", temperamento="tranquilo")
    db.session.add(mascota_extra)
    db.session.flush()
    db.session.add(MascotaDueno(mascota_id=mascota_extra.id, cliente_id=cliente.id, es_principal=False))

    otro_usuario = Usuario(email="otro-cliente@test.com", rol_id=rol_cliente.id, estado_activo=True)
    otro_usuario.set_password("pass")
    db.session.add(otro_usuario)
    db.session.flush()
    otro_cliente = Cliente(usuario_id=otro_usuario.id, nombre="Otro", apellido="Cliente", telefono="591-70000001")
    db.session.add(otro_cliente)
    db.session.flush()
    mascota_otro = Mascota(nombre="Mishi", especie="gato", raza="Criollo", temperamento="tranquilo")
    db.session.add(mascota_otro)
    db.session.flush()
    db.session.add(MascotaDueno(mascota_id=mascota_otro.id, cliente_id=otro_cliente.id, es_principal=True))
    db.session.commit()

    response = client.get("/api/clientes/me/mascotas", headers=auth(token_cliente))
    assert response.status_code == 200
    data = response.get_json()["data"]
    nombres = {item["nombre"] for item in data["mascotas"]}
    assert {"Luna", "Kira"}.issubset(nombres)
    assert "Mishi" not in nombres

    delete_response = client.delete(
        f"/api/clientes/me/mascotas/{mascota_extra.id}",
        headers=auth(token_cliente),
    )
    assert delete_response.status_code == 200
    assert Mascota.query.filter_by(id=mascota_extra.id).first() is not None
    assert MascotaDueno.query.filter_by(mascota_id=mascota_extra.id, cliente_id=cliente.id).first() is None


def test_cliente_solicita_cita_y_recibe_notificacion_listo_para_recoger(client, token_cliente, token_recep):
    from app.extensions import db
    from app.models import Cita, Encuesta
    from app.models.agenda import DisponibilidadGroomer

    fecha = datetime(2099, 1, 6, 11, 0, 0)
    dia_semana = int(fecha.strftime("%w"))
    disponibilidad = DisponibilidadGroomer(
        groomer_id=1,
        dia_semana=dia_semana,
        hora_inicio=time(9, 0),
        hora_fin=time(18, 0),
        buffer_minutos=15,
        activo=True,
        intervalo_descanso={"inicio": "13:00", "fin": "14:00"},
    )
    db.session.add(disponibilidad)
    db.session.commit()

    response = client.post(
        "/api/solicitudes-cita",
        json={
            "mascota_id": 1,
            "groomer_id": 1,
            "servicio_id": 1,
            "fecha_hora_inicio": fecha.isoformat(),
            "notas": "Cliente necesita ajuste de horario",
        },
        headers=auth(token_cliente),
    )
    assert response.status_code == 201
    cita_data = response.get_json()["data"]
    cita_id = cita_data["id"]
    assert cita_data["estado"] == "pendiente"

    citas_response = client.get("/api/clientes/me/citas", headers=auth(token_cliente))
    assert citas_response.status_code == 200
    citas = citas_response.get_json()["data"]["citas"]
    assert any(item["id"] == cita_id for item in citas)

    completar_response = client.patch(
        f"/api/citas/{cita_id}/estado",
        json={"estado": "completada"},
        headers=auth(token_recep),
    )
    assert completar_response.status_code == 200

    notificaciones_response = client.get("/api/clientes/me/notificaciones", headers=auth(token_cliente))
    assert notificaciones_response.status_code == 200
    notificaciones = notificaciones_response.get_json()["data"]["notificaciones"]
    assert any(item["tipo_evento"] == "listo_recoger" for item in notificaciones)

    encuesta_response = client.post(
        f"/api/encuestas/{cita_id}",
        json={"calificacion": 5, "nps": 9, "comentario": "Muy buen servicio"},
        headers=auth(token_cliente),
    )
    assert encuesta_response.status_code == 200
    encuesta = Encuesta.query.filter_by(cita_id=cita_id).first()
    assert encuesta is not None
    assert encuesta.respondida is True


def test_cliente_no_puede_cancelar_con_menos_de_24_horas(client, token_cliente):
    from app.extensions import db
    from app.models import Cita

    inicio = datetime.now(timezone.utc) + timedelta(hours=10)
    cita = Cita(
        mascota_id=1,
        groomer_id=1,
        servicio_id=1,
        fecha_hora_inicio=inicio,
        fecha_hora_fin=inicio + timedelta(hours=1),
        duracion_estimada=60,
        precio_estimado=80.0,
        estado="agendada",
    )
    db.session.add(cita)
    db.session.commit()

    response = client.patch(
        f"/api/clientes/me/citas/{cita.id}/cancelar",
        json={"motivo_cancelacion": "No puedo asistir"},
        headers=auth(token_cliente),
    )
    assert response.status_code == 422


def test_cliente_historial_no_expone_ventas_admin(client, token_cliente):
    # The route is intentionally scoped to personal history only.
    response = client.get("/api/clientes/me/citas", headers=auth(token_cliente))
    assert response.status_code == 200
    citas = response.get_json()["data"]["citas"]
    for item in citas:
        assert "ventas" not in item
        assert "total" not in item
        assert "ticket" not in item


def auth(token):
    return {"Authorization": f"Bearer {token}"}
