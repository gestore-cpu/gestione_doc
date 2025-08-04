from extensions import db, bcrypt
from models import User
from app import app  # Importa l'oggetto Flask


def create_admin_user():
    """Crea un utente admin con username, email e password specificati se non esiste già."""
    username = "admin"
    email = "gobbomauro77@yahoo.it"
    password_plain = "Smemorato12!"

    existing_user = User.query.filter(
        (User.username == username) | (User.email == email)
    ).first()

    if existing_user:
        print(f"Utente già esistente: {existing_user.username} - {existing_user.email}")
        return

    hashed_password = bcrypt.generate_password_hash(password_plain).decode('utf-8')
    new_admin = User(
        username=username,
        email=email,
        password=hashed_password,
        role='admin',
        can_download=True
    )
    db.session.add(new_admin)
    db.session.commit()
    print(f"Utente admin '{username}' creato con successo.")


if __name__ == "__main__":
    with app.app_context():
        create_admin_user() 