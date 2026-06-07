from datetime import datetime, time

from tests.conftest import auth


def test_solicitud_cita_crea_estado_agendada(client, token_cliente):
    from app.extensions import db
    from app.models import Groomer
    from app.models.agenda import DisponibilidadGroomer

    fecha_objetivo = datetime.strptime("2099-06-15", "%Y-%m-%d")
    groomer = Groomer.query.filter_by(estado_activo=True).first()
    assert groomer is not None
    for dia_semana in range(7):
        disponibilidad = DisponibilidadGroomer.query.filter_by(groomer_id=groomer.id, dia_semana=dia_semana).first()
        if not disponibilidad:
            db.session.add(
                DisponibilidadGroomer(
                    groomer_id=groomer.id,
                    dia_semana=dia_semana,
                    hora_inicio=time(9, 0),
                    hora_fin=time(18, 0),
                    intervalo_descanso={"inicio": "13:00", "fin": "14:00"},
                    buffer_minutos=15,
                    activo=True,
                )
            )
    db.session.commit()

    r = client.post(
        '/api/solicitudes-cita',
        json={'mascota_id': 1, 'servicio_id': 1, 'fecha_preferida': '2099-06-15', 'franja': 'manana'},
        headers=auth(token_cliente),
    )
    assert r.status_code in (200, 201)
    assert r.json['data']['estado'] == 'agendada'


def test_solicitud_fecha_pasada_rechazada(client, token_cliente):
    r = client.post(
        '/api/solicitudes-cita',
        json={'mascota_id': 1, 'servicio_id': 1, 'fecha_preferida': '2020-01-01', 'franja': 'manana'},
        headers=auth(token_cliente),
    )
    assert r.status_code == 422


def test_solicitud_mascota_ajena_rechazada(client, token_cliente):
    r = client.post(
        '/api/solicitudes-cita',
        json={'mascota_id': 9999, 'servicio_id': 1, 'fecha_preferida': '2099-06-15', 'franja': 'tarde'},
        headers=auth(token_cliente),
    )
    assert r.status_code == 404


def test_fechas_disponibles_retorna_lista(client, token_cliente):
    r = client.get(
        '/api/agenda/fechas-disponibles?servicio_id=1&mascota_id=1',
        headers=auth(token_cliente),
    )
    assert r.status_code == 200
    assert 'fechas_disponibles' in r.json['data']
    assert isinstance(r.json['data']['fechas_disponibles'], list)
