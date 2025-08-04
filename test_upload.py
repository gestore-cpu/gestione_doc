import io
import pytest
from app import app, db
from models import User, Company, Department, Document
from extensions import bcrypt
from werkzeug.datastructures import MultiDict

@pytest.fixture
def client():
    """Crea un client di test con database temporaneo e dati iniziali."""
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False  # Disabilita CSRF nei test

    with app.test_client() as client:
        with app.app_context():
            db.drop_all()
            db.create_all()

            # === Crea dati iniziali ===
            company = Company(name='TestCorp')
            department = Department(name='IT', company=company)
            db.session.add_all([company, department])
            db.session.flush()

            # === Crea utente di test con password bcrypt ===
            raw_password = 'TestPassword123!'
            hashed_password = bcrypt.generate_password_hash(raw_password).decode('utf-8')

            user = User(
                email='testuser@example.com',
                username='testuser',
                password=hashed_password
            )
            user.companies.append(company)
            user.departments.append(department)
            db.session.add(user)
            db.session.commit()

            # === Verifica che l'hash sia stato salvato ===
            saved_user = User.query.filter_by(email='testuser@example.com').first()

        yield client

def test_upload_document(client):
    """Testa login e caricamento documento, verificando sia HTML che database."""

    # === LOGIN ===
    login_data = MultiDict({
        'email': 'testuser@example.com',
        'password': 'TestPassword123!'
    })

    login_response = client.post('/auth/login', data=login_data, follow_redirects=True)

    with open("debug_login.html", "w", encoding="utf-8") as f:
        f.write(login_response.data.decode("utf-8"))

    assert login_response.status_code == 200

    html = login_response.data.decode("utf-8")
    assert '<title>Benvenuto</title>' in html, "⚠️ Login non ha portato alla pagina principale correttamente"

    # === UPLOAD DOCUMENTO ===
    file_name = 'testfile.txt'
    upload_data = {
        'file': (io.BytesIO(b'Test file content'), file_name),
        'title': 'Documento di test',
        'visibility': 'pubblico',
        'destination': 'local',  # Campo richiesto dal form anche se non usato
        'upload_to_drive': 'false',
    }

    upload_response = client.post(
        '/upload_to_drive',
        data=upload_data,
        content_type='multipart/form-data',
        follow_redirects=True
    )

    assert upload_response.status_code == 200
    assert b'Documento caricato con successo' in upload_response.data

    # === VERIFICA DATABASE ===
    with app.app_context():
        doc = Document.query.filter_by(title='Documento di test').first()
        assert doc is not None, "⚠️ Documento non trovato nel database"
        assert doc.original_filename == file_name
        assert doc.filename != file_name  # Il nome file deve essere stato rinominato (es. UUID o timestamp)
