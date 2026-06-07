from app.extensions import db


def test_recomendaciones_sin_mascota(client):
    r = client.get("/api/productos/recomendados")
    assert r.status_code == 200
    data = r.get_json() or {}
    assert "recomendaciones" in data


def test_recomendaciones_con_mascota(client, token_cliente):
    from app.models.mascota import Mascota
    from app.models.inventario import Producto

    with client.application.app_context():
        producto = Producto(nombre="Snack perro", sku="SN-001", precio_base=5, stock=20, activo=True)
        db.session.add(producto)
        mascota = Mascota(nombre="Testie", especie="perro", peso_kg=8.0, temperamento="tranquilo")
        db.session.add(mascota)
        db.session.commit()
        pid = producto.id
        mid = mascota.id

    r = client.get(f"/api/productos/recomendados?mascota_id={mid}", headers={"Authorization": f"Bearer {token_cliente}"})
    assert r.status_code == 200
    data = r.get_json() or {}
    assert data.get("recomendaciones") is not None
    assert len(data.get("recomendaciones")) <= 6
