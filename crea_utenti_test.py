from extensions import db, bcrypt
from models import User
from datetime import datetime

# ✅ Importa l'app Flask
from app import app  # <-- sostituisci con il percorso corretto se diverso

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

    with app.app_context():
        for u in utenti:
            if not User.query.filter_by(username=u['username']).first():
                if not password_valida(u['password']):
                    continue

                new_user = User(
                    username=u['username'],
                    email=u['email'],
                    password=bcrypt.generate_password_hash(u['password']).decode('utf-8'),
                    role=u['role'],
                    password_set_at=datetime.utcnow()
                )
                db.session.add(new_user)
            else:
                pass

        db.session.commit()

if __name__ == "__main__":
    crea_utenti()

