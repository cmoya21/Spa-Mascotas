from datetime import datetime, timedelta, timezone

from .extensions import db
from .models import AuditLog, Producto, SalidaInsumo
from .services.auth_service import cleanup_blocklist

try:
    from apscheduler.schedulers.background import BackgroundScheduler
except Exception:
    BackgroundScheduler = None


_scheduler = None


def analizar_consumo_elevado_job(app):
    with app.app_context():
        ahora = datetime.now(timezone.utc)
        hace_7 = ahora - timedelta(days=7)
        hace_37 = ahora - timedelta(days=37)

        rows = db.session.query(SalidaInsumo.producto_id, SalidaInsumo.cantidad_usada, SalidaInsumo.entregado_en).filter(
            SalidaInsumo.entregado_en >= hace_37
        ).all()

        stats = {}
        for producto_id, cantidad_usada, entregado_en in rows:
            pid = int(producto_id)
            cantidad = float(cantidad_usada or 0)
            slot = stats.setdefault(pid, {"reciente": 0.0, "historico": 0.0})
            if entregado_en and entregado_en >= hace_7:
                slot["reciente"] += cantidad
            else:
                slot["historico"] += cantidad

        productos = {item.id: item for item in Producto.query.filter(Producto.id.in_(list(stats.keys()))).all()} if stats else {}

        for producto_id, data in stats.items():
            consumo_reciente = float(data["reciente"] or 0)
            consumo_historico = float(data["historico"] or 0)
            if consumo_reciente <= 0 or consumo_historico <= 0:
                continue

            consumo_diario_historico = consumo_historico / 30.0
            umbral = consumo_diario_historico * 7.0 * 2.0
            if consumo_reciente <= umbral:
                continue

            factor = consumo_reciente / max((consumo_historico / 7.0), 0.0001)
            producto = productos.get(producto_id)

            db.session.add(
                AuditLog(
                    tabla="productos",
                    operacion="UPDATE",
                    registro_id=producto_id,
                    datos_despues={
                        "alerta": "consumo_elevado",
                        "producto_id": producto_id,
                        "producto_nombre": producto.nombre if producto else None,
                        "consumo_7dias": consumo_reciente,
                        "consumo_diario_promedio": consumo_diario_historico,
                        "factor_anomalia": round(factor, 2),
                    },
                )
            )

        db.session.commit()


def init_scheduler(app):
    global _scheduler
    if BackgroundScheduler is None:
        return None
    if _scheduler is not None:
        return _scheduler

    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(
        id="analisis_consumo",
        func=lambda: analizar_consumo_elevado_job(app),
        trigger="interval",
        hours=24,
    )
    scheduler.add_job(
        id="limpieza_token_blocklist",
        func=lambda: cleanup_blocklist(),
        trigger="interval",
        hours=24,
    )
    scheduler.start()
    _scheduler = scheduler
    return scheduler
