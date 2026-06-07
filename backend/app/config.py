import os
import secrets
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "..", "uploads")
os.makedirs(os.path.join(UPLOAD_FOLDER, "mascotas", "fotos"), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, "mascotas", "carnets"), exist_ok=True)
MAX_CONTENT_LENGTH = 10 * 1024 * 1024


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "change_me")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = UPLOAD_FOLDER
    MAX_CONTENT_LENGTH = MAX_CONTENT_LENGTH

    _jwt_secret = os.environ.get("JWT_SECRET_KEY") or ""
    JWT_SECRET_KEY = _jwt_secret if len(_jwt_secret) >= 32 else secrets.token_hex(32)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(seconds=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", "3600")))
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(seconds=int(os.getenv("JWT_REFRESH_TOKEN_EXPIRES", "2592000")))
    JWT_ALGORITHM = "HS256"
    JWT_TOKEN_LOCATION = ["headers"]
    JWT_HEADER_NAME = "Authorization"
    JWT_HEADER_TYPE = "Bearer"
    JWT_BLACKLIST_ENABLED = True
    JWT_BLACKLIST_TOKEN_CHECKS = ["access", "refresh"]

    BCRYPT_LOG_ROUNDS = int(os.getenv("BCRYPT_LOG_ROUNDS", "12"))
    CORS_ORIGINS = [os.getenv("FRONTEND_URL", "http://localhost:5173")]

    SMTP_HOST = os.getenv("SMTP_HOST", "")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM = os.getenv("SMTP_FROM", "no-reply@petspa.local")
    SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
    TELEFONO_SPA = os.getenv("TELEFONO_SPA", "recepción")

    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_OAUTH_REDIRECT = os.getenv("GOOGLE_OAUTH_REDIRECT", "")
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
