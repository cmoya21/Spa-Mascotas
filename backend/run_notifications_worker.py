from app import create_app
from app.services.notifications_worker import process_pending_notifications


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        total = process_pending_notifications()
        print(f"Notificaciones procesadas: {total}")
