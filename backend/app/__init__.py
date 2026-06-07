from flask import Flask

from .config import Config
from .extensions import init_extensions, db, jwt
from .bootstrap import seed_catalogo_basico
from .scheduler import init_scheduler
from pathlib import Path
from flask import send_from_directory
from flask_apscheduler import APScheduler
from .models import Promocion, TokenBlocklist


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    init_extensions(app)
    # Lazy import to reduce startup issues from circular imports.
    from .routes import (
        auth_bp,
        admin_bp,
        agenda_bp,
        mascotas_bp,
        grooming_bp,
        notificaciones_bp,
        insumos_bp,
        productos_insumos_bp,
        inventario_bp,
        pagos_bp,
        citas_bp,
        clientes_bp,
        pedidos_bp,
        alertas_bp,
        cobros_bp,
        disponibilidad_bp,
        servicios_bp,
        groomers_bp,
        fichas_bp,
        reportes_bp,
        promociones_bp,
        tienda_bp,
        encuestas_bp,
        usuarios_bp,
    )

    from werkzeug.exceptions import HTTPException
    from flask import jsonify

    @app.errorhandler(HTTPException)
    def handle_http_exception(exc):
        description = exc.description if isinstance(exc.description, dict) else None
        if description:
            payload = description
        else:
            payload = {"success": False, "message": exc.description or exc.name}
        return jsonify(payload), exc.code or 500

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(agenda_bp)
    app.register_blueprint(mascotas_bp)
    app.register_blueprint(grooming_bp)
    app.register_blueprint(notificaciones_bp)
    app.register_blueprint(insumos_bp)
    app.register_blueprint(productos_insumos_bp)
    app.register_blueprint(inventario_bp)
    app.register_blueprint(pagos_bp)
    app.register_blueprint(citas_bp)
    app.register_blueprint(clientes_bp)
    app.register_blueprint(pedidos_bp)
    app.register_blueprint(alertas_bp)
    app.register_blueprint(cobros_bp)
    app.register_blueprint(disponibilidad_bp)
    app.register_blueprint(servicios_bp)
    app.register_blueprint(groomers_bp)
    app.register_blueprint(fichas_bp)
    app.register_blueprint(reportes_bp)
    app.register_blueprint(promociones_bp)
    app.register_blueprint(tienda_bp)
    app.register_blueprint(encuestas_bp)
    app.register_blueprint(usuarios_bp)

    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(_jwt_header, jwt_payload):
        jti = jwt_payload.get("jti")
        return TokenBlocklist.query.filter_by(jti=jti).first() is not None if jti else True

    @app.after_request
    def add_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if not app.debug:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    try:
        with app.app_context():
            Promocion.__table__.create(bind=db.engine, checkfirst=True)
    except Exception:
        app.logger.exception("No se pudo verificar la tabla de promociones.")

    # expose uploads directory (configured via UPLOAD_FOLDER or default to <app>/uploads)
    upload_root = app.config.get('UPLOAD_FOLDER') or (Path(app.root_path) / 'uploads')

    @app.route('/uploads/<path:filename>')
    def uploads(filename):
        return send_from_directory(str(upload_root), filename)

    @app.before_request
    def ensure_catalogo_basico():
        seed_catalogo_basico()

    if not app.config.get("TESTING"):
        notif_scheduler = APScheduler()
        app.config.setdefault("SCHEDULER_API_ENABLED", False)
        notif_scheduler.init_app(app)
        if not notif_scheduler.running:
            app_ref = app

            def notif_job():
                with app_ref.app_context():
                    from app.utils.notif_worker import _procesar_interno

                    return _procesar_interno(app_ref)

            notif_scheduler.add_job(
                id="notif_worker",
                func=notif_job,
                trigger="interval",
                seconds=60,
            )
            notif_scheduler.start()
        app.extensions["notif_scheduler"] = notif_scheduler
        init_scheduler(app)

    return app
