"""
Fixtures pytest per test DOCS Mercury.
"""

import pytest
import tempfile
import os
from datetime import datetime, timedelta
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from werkzeug.security import generate_password_hash

# Import app components
from extensions import db, bcrypt, mail
from models import User, Company, Department, Document, DocumentActivityLog, DownloadDeniedLog, AuthorizedAccess
from app import create_app

@pytest.fixture(scope='session')
def app():
    """
    Crea app Flask per testing con database SQLite in-memory.
    """
    # Configurazione test
    app = create_app()
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'WTF_CSRF_ENABLED': False,
        'SECRET_KEY': 'test-secret-key',
        'MAIL_SUPPRESS_SEND': True
    })
    
    return app

@pytest.fixture(scope='function')
def client(app):
    """
    Test client Flask.
    """
    with app.test_client() as client:
        yield client

@pytest.fixture(scope='function')
def database(app):
    """
    Database SQLite in-memory con dati di test.
    """
    with app.app_context():
        # Crea tabelle
        db.create_all()
        
        # Popola dati di test
        create_test_data()
        
        yield db
        
        # Cleanup
        db.session.remove()
        db.drop_all()

def create_test_data():
    """
    Crea dati di test per Mercury e altri moduli.
    """
    # Aziende
    mercury_company = Company(name="Mercury Tech", created_at=datetime.utcnow())
    other_company = Company(name="Altro Modulo", created_at=datetime.utcnow())
    db.session.add_all([mercury_company, other_company])
    
    # Reparti
    it_dept = Department(name="IT", company_id=1, created_at=datetime.utcnow())
    hr_dept = Department(name="HR", company_id=1, created_at=datetime.utcnow())
    other_dept = Department(name="Altro Reparto", company_id=2, created_at=datetime.utcnow())
    db.session.add_all([it_dept, hr_dept, other_dept])
    
    # Utenti Mercury
    mercury_admin = User(
        username="admin.mercury",
        email="admin@mercury.com",
        first_name="Admin",
        last_name="Mercury",
        password_hash=generate_password_hash("password123"),
        role="admin",
        modulo="Mercury",
        company_id=1,
        department_id=1,
        created_at=datetime.utcnow(),
        last_login=datetime.utcnow()
    )
    
    mercury_user = User(
        username="user.mercury",
        email="user@mercury.com",
        first_name="User",
        last_name="Mercury",
        password_hash=generate_password_hash("password123"),
        role="user",
        modulo="Mercury",
        company_id=1,
        department_id=1,
        created_at=datetime.utcnow(),
        last_login=datetime.utcnow() - timedelta(hours=2)
    )
    
    # Utenti altri moduli
    other_admin = User(
        username="admin.other",
        email="admin@other.com",
        first_name="Admin",
        last_name="Other",
        password_hash=generate_password_hash("password123"),
        role="admin",
        modulo="Other",
        company_id=2,
        department_id=3,
        created_at=datetime.utcnow()
    )
    
    # CEO
    ceo_user = User(
        username="ceo",
        email="ceo@company.com",
        first_name="CEO",
        last_name="Company",
        password_hash=generate_password_hash("password123"),
        role="ceo",
        modulo="All",
        company_id=1,
        department_id=1,
        created_at=datetime.utcnow()
    )
    
    # Guest Mercury
    mercury_guest = User(
        username="guest.mercury",
        email="guest@mercury.com",
        first_name="Guest",
        last_name="Mercury",
        password_hash=generate_password_hash("temp123"),
        role="guest",
        modulo="Mercury",
        company_id=1,
        department_id=1,
        access_expiration=datetime.utcnow() + timedelta(days=30),
        created_at=datetime.utcnow()
    )
    
    # Guest scaduto
    expired_guest = User(
        username="expired.guest",
        email="expired@mercury.com",
        first_name="Expired",
        last_name="Guest",
        password_hash=generate_password_hash("temp123"),
        role="guest",
        modulo="Mercury",
        company_id=1,
        department_id=1,
        access_expiration=datetime.utcnow() - timedelta(days=1),
        created_at=datetime.utcnow()
    )
    
    db.session.add_all([
        mercury_admin, mercury_user, other_admin, ceo_user,
        mercury_guest, expired_guest
    ])
    
    # Documenti
    doc1 = Document(
        title="Manuale Sicurezza 2024.pdf",
        filename="manuale_sicurezza.pdf",
        file_path="/documents/manuale_sicurezza.pdf",
        company_id=1,
        department_id=1,
        uploaded_by=1,
        created_at=datetime.utcnow()
    )
    
    doc2 = Document(
        title="Procedure Operative.docx",
        filename="procedure_operative.docx",
        file_path="/documents/procedure_operative.docx",
        company_id=1,
        department_id=1,
        uploaded_by=1,
        created_at=datetime.utcnow()
    )
    
    db.session.add_all([doc1, doc2])
    
    # Attività documenti
    activity1 = DocumentActivityLog(
        user_id=2,  # mercury_user
        document_id=1,
        action="view",
        timestamp=datetime.utcnow()
    )
    
    activity2 = DocumentActivityLog(
        user_id=5,  # mercury_guest
        document_id=1,
        action="download",
        timestamp=datetime.utcnow()
    )
    
    db.session.add_all([activity1, activity2])
    
    # Accessi autorizzati per guest
    auth_access = AuthorizedAccess(
        user_id=5,  # mercury_guest
        document_id=1,
        granted_at=datetime.utcnow()
    )
    
    db.session.add(auth_access)
    
    db.session.commit()

@pytest.fixture
def mercury_admin_session(client, database):
    """
    Sessione autenticata come admin Mercury.
    """
    with client.session_transaction() as sess:
        sess['user_id'] = 1  # mercury_admin
        sess['role'] = 'admin'
        sess['modulo'] = 'Mercury'
    return client

@pytest.fixture
def ceo_session(client, database):
    """
    Sessione autenticata come CEO.
    """
    with client.session_transaction() as sess:
        sess['user_id'] =4  # ceo_user
        sess['role'] = 'ceo'
        sess['modulo'] = 'All'
    return client

@pytest.fixture
def mercury_user_session(client, database):
    """
    Sessione autenticata come user Mercury.
    """
    with client.session_transaction() as sess:
        sess['user_id'] = 2  # mercury_user
        sess['role'] = 'user'
        sess['modulo'] = 'Mercury'
    return client

@pytest.fixture
def other_admin_session(client, database):
    """
    Sessione autenticata come admin altro modulo.
    """
    with client.session_transaction() as sess:
        sess['user_id'] = 3  # other_admin
        sess['role'] = 'admin'
        sess['modulo'] = 'Other'
    return client 