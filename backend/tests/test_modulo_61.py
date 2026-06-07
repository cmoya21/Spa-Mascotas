from datetime import datetime

import pytest


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def modulo_61_seed(app):
    with app.app_context():
        from app.extensions import db
        from app.models.agenda import Cita, DisponibilidadGroomer, Servicio
        from app.models.encuesta import Encuesta
        from app.models.grooming import ChecklistItemTemplate, FichaChecklist, FichaGrooming
        from app.models.mascota import Mascota, MascotaDueno
        from app.models.notificacion import Notificacion
        from app.models.usuario import Cliente, Groomer, Usuario

        groomer = Groomer.query.join(Usuario).filter(Usuario.email == "groomer@test.com").first()
        cliente = Cliente.query.join(Usuario).filter(Usuario.email == "cliente@test.com").first()
        servicio = Servicio.query.first()

        if not groomer or not cliente or not servicio:
            raise RuntimeError("Datos base faltantes para el módulo 6.1")

        for dia in [0, 1, 2, 3, 4]:
            if not DisponibilidadGroomer.query.filter_by(groomer_id=groomer.id, dia_semana=dia).first():
                db.session.add(
                    DisponibilidadGroomer(
                        groomer_id=groomer.id,
                        dia_semana=dia,
                        hora_inicio=datetime.strptime("09:00", "%H:%M").time(),
                        hora_fin=datetime.strptime("18:00", "%H:%M").time(),
                        buffer_minutos=15,
                        activo=True,
                    )
                )

        mascota = Mascota.query.filter_by(nombre="Luna modulo 61").first()
        if not mascota:
            mascota = Mascota(
                nombre="Luna modulo 61",
                especie="perro",
                raza="Poodle",
                peso_kg=4.2,
                temperamento="tranquilo",
                alergias_conocidas="shampoo fragancia",
            )
            db.session.add(mascota)
            db.session.flush()
            if not MascotaDueno.query.filter_by(mascota_id=mascota.id, cliente_id=cliente.id).first():
                db.session.add(MascotaDueno(mascota_id=mascota.id, cliente_id=cliente.id, es_principal=True))
            db.session.flush()

        template = ChecklistItemTemplate.query.filter_by(servicio_id=servicio.id).first()
        if not template:
            template = ChecklistItemTemplate(
                servicio_id=servicio.id,
                nombre="Revisión de pelaje",
                requiere_obs=False,
                orden=1,
                activo=True,
            )
            db.session.add(template)
            db.session.flush()

        cita = Cita.query.filter_by(fecha_hora_inicio=datetime(2025, 5, 27, 9, 0)).first()
        if not cita:
            cita = Cita(
                mascota_id=mascota.id,
                groomer_id=groomer.id,
                servicio_id=servicio.id,
                fecha_hora_inicio=datetime(2025, 5, 27, 9, 0),
                fecha_hora_fin=datetime(2025, 5, 27, 10, 30),
                duracion_estimada=90,
                estado="completada",
                notas="Primera cita de prueba",
                creado_por=cliente.usuario_id,
            )
            db.session.add(cita)
            db.session.flush()

        if not FichaGrooming.query.filter_by(cita_id=cita.id).first():
            ficha = FichaGrooming(
                cita_id=cita.id,
                groomer_id=groomer.id,
                checklist_completo=True,
                fecha_cierre=datetime(2025, 5, 27, 11, 0),
            )
            db.session.add(ficha)
            db.session.flush()
            if not FichaChecklist.query.filter_by(ficha_id=ficha.id, item_id=template.id).first():
                db.session.add(
                    FichaChecklist(
                        ficha_id=ficha.id,
                        item_id=template.id,
                        completado=True,
                        completado_en=datetime(2025, 5, 27, 10, 0),
                    )
                )
            if not Notificacion.query.filter_by(cita_id=cita.id).first():
                db.session.add(
                    Notificacion(
                        cita_id=cita.id,
                        cliente_id=cliente.id,
                        tipo_canal="email",
                        tipo_evento="listo_recoger",
                        destino=cliente.usuario.email,
                        mensaje="Tu mascota está lista para ser recogida.",
                        fecha_programacion=datetime(2025, 5, 27, 11, 5),
                        fecha_envio=datetime(2025, 5, 27, 11, 6),
                        estado="enviado",
                    )
                )
            if not Encuesta.query.filter_by(cita_id=cita.id).first():
                db.session.add(
                    Encuesta(
                        cita_id=cita.id,
                        cliente_id=cliente.id,
                        calificacion=5,
                        respondida=True,
                        respondida_en=datetime(2025, 5, 27, 12, 0),
                    )
                )

        if not Cita.query.filter_by(fecha_hora_inicio=datetime(2025, 5, 27, 13, 0)).first():
            db.session.add(
                Cita(
                    mascota_id=mascota.id,
                    groomer_id=groomer.id,
                    servicio_id=servicio.id,
                    fecha_hora_inicio=datetime(2025, 5, 27, 13, 0),
                    fecha_hora_fin=datetime(2025, 5, 27, 14, 0),
                    duracion_estimada=60,
                    estado="confirmada",
                    notas="Segunda cita de prueba",
                    creado_por=cliente.usuario_id,
                )
            )

        if not Cita.query.filter_by(fecha_hora_inicio=datetime(2025, 5, 28, 10, 0)).first():
            db.session.add(
                Cita(
                    mascota_id=mascota.id,
                    groomer_id=groomer.id,
                    servicio_id=servicio.id,
                    fecha_hora_inicio=datetime(2025, 5, 28, 10, 0),
                    fecha_hora_fin=datetime(2025, 5, 28, 11, 0),
                    duracion_estimada=60,
                    estado="agendada",
                    notas="Tercera cita de prueba",
                    creado_por=cliente.usuario_id,
                )
            )

        db.session.commit()
        return {"groomer_id": groomer.id}


def test_groomer_solo_ve_sus_citas(client, token_groomer, modulo_61_seed):
    r = client.get("/api/groomers/me/agenda?fecha=2025-05-27", headers=_auth(token_groomer))
    assert r.status_code == 200
    payload = r.get_json()
    assert isinstance(payload, list)
    for cita in payload:
        assert "mascota" in cita
        assert "servicio" in cita
        assert "ficha" in cita
        assert cita["mascota"]["nombre"]
        assert cita["servicio"]["nombre"]


def test_groomer_agenda_semana(client, token_groomer, modulo_61_seed):
    r = client.get("/api/groomers/me/agenda/semana?fecha=2025-05-27", headers=_auth(token_groomer))
    assert r.status_code == 200
    payload = r.get_json()
    assert "dias" in payload
    assert "resumen" in payload
    assert len(payload["dias"]) == 7


def test_cliente_no_accede_agenda_groomer(client, token_cliente):
    r = client.get("/api/groomers/me/agenda", headers=_auth(token_cliente))
    assert r.status_code == 403


def test_admin_no_accede_agenda_groomer(client, token_admin):
    r = client.get("/api/groomers/me/agenda", headers=_auth(token_admin))
    assert r.status_code == 403


def test_fecha_invalida_retorna_422(client, token_groomer):
    r = client.get("/api/groomers/me/agenda?fecha=no-es-fecha", headers=_auth(token_groomer))
    assert r.status_code == 422


def test_stats_groomer(client, token_groomer, modulo_61_seed):
    r = client.get("/api/groomers/me/stats", headers=_auth(token_groomer))
    assert r.status_code == 200
    payload = r.get_json()
    assert "citas_hoy" in payload
    assert "completadas_hoy" in payload
    assert "citas_semana" in payload
    assert "promedio_calificacion" in payload
