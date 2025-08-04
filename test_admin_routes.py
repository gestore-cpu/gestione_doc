import pytest
from app import app, db
from models import User, Company, Department, Document
from flask.testing import FlaskClient
from datetime import date
from extensions import bcrypt

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client
        with app.app_context():
            db.drop_all()

def login_admin(client: FlaskClient):
    # Effettua login come admin fittizio
    admin = User(username='admin', email='admin@example.com', role='admin')
    admin.password = 'adminpass'  # Assicurati che la password sia gestita correttamente
    db.session.add(admin)
    db.session.commit()
    client.post('/login', data={'username': 'admin', 'password': 'adminpass'}, follow_redirects=True)
    return admin

def test_update_guest_user(client):
    with app.app_context():
        # Setup: crea utente guest, documenti visibili
        hashed_password = bcrypt.generate_password_hash('GuestPassword123!').decode('utf-8')
        guest = User(username='guest1', email='guest@example.com', role='guest', can_download=True, password=hashed_password)
        db.session.add(guest)
        db.session.commit()
        # Creo company e dept dummy per i documenti
        company = Company(name='DummyCo')
        dept = Department(name='DummyDept', company=company)
        db.session.add_all([company, dept])
        db.session.commit()
        # Ricarico company e dept dal DB
        company = Company.query.filter_by(name='DummyCo').first()
        dept = Department.query.filter_by(name='DummyDept').first()
        doc1 = Document(title='File 1', filename='file1.pdf', original_filename='file1.pdf', uploader=guest, uploader_email=guest.email, company_id=company.id, department_id=dept.id)
        db.session.add(doc1)
        db.session.commit()

    # Login admin
    with app.app_context():
        login_admin(client)
        # Ricarico guest dal DB prima del POST
        guest = User.query.filter_by(email='guest@example.com').first()
        doc1 = Document.query.filter_by(title='File 1').first()

    # Simula POST di aggiornamento guest con revoca documento e nuova scadenza
    response = client.post(f'/admin/users/{guest.id}/update', data={
        'username': 'guest1',
        'email': 'guest@example.com',
        'role': 'guest',
        # 'can_download' non presente = non spuntato
        'access_expiration': '2025-12-31',
        'revoke_docs': [str(doc1.id)],
    }, follow_redirects=True)

    assert response.status_code == 200
    updated_guest = User.query.get(guest.id)
    db.session.refresh(updated_guest)
    print(f"[TEST DEBUG] updated_guest.can_download={updated_guest.can_download}")
    assert updated_guest.can_download is False
    assert updated_guest.access_expiration == date(2025, 12, 31)
    assert doc1 not in updated_guest.documents

def test_update_normal_user(client):
    with app.app_context():
        # Setup: utente normale + aziende/reparti
        company = Company(name='TestCo')
        dept = Department(name='Logistica', company=company)
        hashed_password = bcrypt.generate_password_hash('UserPassword123!').decode('utf-8')
        user = User(username='user1', email='user1@example.com', role='user', password=hashed_password)
        user.companies.append(company)
        user.departments.append(dept)
        db.session.add_all([company, dept, user])
        db.session.commit()
        # Ricarico user, company, dept dal DB per evitare DetachedInstanceError
        user = User.query.filter_by(email='user1@example.com').first()
        company = Company.query.filter_by(name='TestCo').first()
        dept = Department.query.filter_by(name='Logistica').first()

    # Login admin
    with app.app_context():
        login_admin(client)

    # Simula POST update con selezione aziende/reparti
    response = client.post(f'/admin/users/{user.id}/update', data={
        'username': 'user1',
        'email': 'user1@example.com',
        'role': 'user',
        'company_ids': [str(company.id)],
        'department_ids': [str(dept.id)],
    }, follow_redirects=True)

    assert response.status_code == 200
    updated = User.query.get(user.id)
    assert company.id in [c.id for c in updated.companies]
    assert dept.id in [d.id for d in updated.departments]
    assert updated.access_expiration is None 