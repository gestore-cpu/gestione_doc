from extensions import db, bcrypt
from models import User
from datetime import datetime

from app import app  # ✅ import corretto della tua Flask app

def password_valida(password):
    return (
        len(password) >= 8 and
        any(c.isdigit() for c in password) and
        any(c.isalpha() for c in password)
    )

def crea_utenti():
    utenti = [
        {'username': 'admin', 'email': 'admin@example.com', 'password': 'Admin123!', 'role': 'admin'},
        {'username': 'user', 'email': 'user@example.com', 'password': 'User123!', 'role': 'user'},
        {'username': 'guest', 'email': 'guest@example.com', 'password': 'Guest123!', 'role': 'guest'},
    ]

    with app.app_context():  # ✅ Necessario per lavorare con Flask e il DB
        for u in utenti:
            if not User.query.filter_by(username=u['username']).first():
                if not password_valida(u['password']):
                    print(f"❌ Password non valida per {u['username']}")
                    continue

                new_user = User(
                    username=u['username'],
                    email=u['email'],
                    password=bcrypt.generate_password_hash(u['password']).decode('utf-8'),
                    role=u['role'],
                    password_set_at=datetime.utcnow()
                )
                db.session.add(new_user)
                print(f"✅ Utente {u['username']} creato")
            else:
                print(f"ℹ️ Utente {u['username']} già esistente")

        db.session.commit()
        print("✔️ Completato.")

if __name__ == "__main__":
    crea_utenti()
