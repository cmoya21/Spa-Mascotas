from authlib.integrations.flask_client import OAuth
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
except Exception:
    Limiter = None
    get_remote_address = None


db = SQLAlchemy()
jwt = JWTManager()
bcrypt = Bcrypt()
migrate = Migrate()
oauth = OAuth()
if Limiter is not None:
    limiter = Limiter(key_func=get_remote_address, default_limits=["200 per day", "50 per hour"], storage_uri="memory://")
else:
    class _LimiterFallback:
        def init_app(self, app):
            return None

        def limit(self, *args, **kwargs):
            def decorator(fn):
                return fn

            return decorator

    limiter = _LimiterFallback()


def init_extensions(app):
    db.init_app(app)
    jwt.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": app.config.get("CORS_ORIGINS", [])}}, supports_credentials=True)
    oauth.init_app(app)
