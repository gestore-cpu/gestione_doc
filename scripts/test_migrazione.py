#!/usr/bin/env python3
"""
Script di test per la migrazione DOCS Mercury.

Verifica la connessione ai database e mostra statistiche senza eseguire la migrazione.
"""

import os
import sys
import logging
from datetime import datetime
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

# Aggiungi il path del progetto
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def setup_logging():
    """Configura il logging per il test."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

logger = setup_logging()

def test_database_connection(url: str, name: str) -> bool:
    """Testa la connessione a un database."""
    try:
        engine = create_engine(url)
        session = sessionmaker(bind=engine)()
        
        # Test connessione
        session.execute(text("SELECT 1"))
        logger.info(f"✅ Connessione {name}: OK")
        
        # Test tabelle
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        logger.info(f"📋 Tabelle {name}: {len(tables)} trovate")
        
        # Mostra tabelle principali
        main_tables = ['users', 'guest_users', 'documents', 'companies', 'departments']
        for table in main_tables:
            if table in tables:
                logger.info(f"   ✅ {table}")
            else:
                logger.warning(f"   ⚠️ {table} (mancante)")
        
        session.close()
        return True
        
    except SQLAlchemyError as e:
        logger.error(f"❌ Connessione {name}: FAILED - {e}")
        return False

def analyze_source_data(source_url: str):
    """Analizza i dati nel database origine."""
    try:
        engine = create_engine(source_url)
        session = sessionmaker(bind=engine)()
        
        logger.info("🔍 ANALISI DATABASE ORIGINE")
        logger.info("=" * 40)
        
        # Conta utenti Mercury
        mercury_users_query = """
            SELECT COUNT(*) as count
            FROM users 
            WHERE company_id IN (
                SELECT id FROM companies WHERE name LIKE '%Mercury%'
            ) OR id IN (
                SELECT user_id FROM user_companies uc 
                JOIN companies c ON uc.company_id = c.id 
                WHERE c.name LIKE '%Mercury%'
            )
        """
        
        result = session.execute(text(mercury_users_query))
        user_count = result.fetchone()[0]
        logger.info(f"👥 Utenti Mercury: {user_count}")
        
        # Conta guest Mercury
        mercury_guests_query = """
            SELECT COUNT(DISTINCT gu.id) as count
            FROM guest_users gu
            WHERE gu.id IN (
                SELECT DISTINCT guest_user_id FROM guest_activities ga
                JOIN documents d ON ga.document_id = d.id
                JOIN companies c ON d.company_id = c.id
                WHERE c.name LIKE '%Mercury%'
            ) OR gu.id IN (
                SELECT DISTINCT guest_user_id FROM guest_comments gc
                JOIN documents d ON gc.document_id = d.id
                JOIN companies c ON d.company_id = c.id
                WHERE c.name LIKE '%Mercury%'
            )
        """
        
        result = session.execute(text(mercury_guests_query))
        guest_count = result.fetchone()[0]
        logger.info(f"👤 Guest Mercury: {guest_count}")
        
        # Conta documenti Mercury
        mercury_docs_query = """
            SELECT COUNT(*) as count
            FROM documents d
            JOIN companies c ON d.company_id = c.id
            WHERE c.name LIKE '%Mercury%'
        """
        
        result = session.execute(text(mercury_docs_query))
        doc_count = result.fetchone()[0]
        logger.info(f"📄 Documenti Mercury: {doc_count}")
        
        # Mostra aziende
        companies_query = """
            SELECT name, COUNT(u.id) as user_count
            FROM companies c
            LEFT JOIN users u ON c.id = u.company_id
            WHERE c.name LIKE '%Mercury%'
            GROUP BY c.id, c.name
        """
        
        result = session.execute(text(companies_query))
        companies = result.fetchall()
        
        logger.info("🏢 Aziende Mercury:")
        for company in companies:
            logger.info(f"   - {company[0]}: {company[1]} utenti")
        
        session.close()
        
    except Exception as e:
        logger.error(f"❌ Errore analisi dati origine: {e}")

def analyze_destination_data(dest_url: str):
    """Analizza i dati nel database destinazione."""
    try:
        engine = create_engine(dest_url)
        session = sessionmaker(bind=engine)()
        
        logger.info("🔍 ANALISI DATABASE DESTINAZIONE")
        logger.info("=" * 40)
        
        # Conta utenti esistenti
        users_query = "SELECT COUNT(*) as count FROM users"
        result = session.execute(text(users_query))
        user_count = result.fetchone()[0]
        logger.info(f"👥 Utenti esistenti: {user_count}")
        
        # Conta guest esistenti
        guests_query = "SELECT COUNT(*) as count FROM guest_users"
        result = session.execute(text(guests_query))
        guest_count = result.fetchone()[0]
        logger.info(f"👤 Guest esistenti: {guest_count}")
        
        # Conta documenti esistenti
        docs_query = "SELECT COUNT(*) as count FROM documents"
        result = session.execute(text(docs_query))
        doc_count = result.fetchone()[0]
        logger.info(f"📄 Documenti esistenti: {doc_count}")
        
        # Mostra ruoli utenti
        roles_query = """
            SELECT role, COUNT(*) as count
            FROM users
            GROUP BY role
            ORDER BY count DESC
        """
        
        result = session.execute(text(roles_query))
        roles = result.fetchall()
        
        logger.info("👑 Distribuzione ruoli:")
        for role in roles:
            logger.info(f"   - {role[0]}: {role[1]} utenti")
        
        session.close()
        
    except Exception as e:
        logger.error(f"❌ Errore analisi dati destinazione: {e}")

def check_duplicates(source_url: str, dest_url: str):
    """Verifica potenziali duplicati."""
    try:
        logger.info("🔍 VERIFICA DUPLICATI")
        logger.info("=" * 40)
        
        # Connessioni
        source_engine = create_engine(source_url)
        dest_engine = create_engine(dest_url)
        
        source_session = sessionmaker(bind=source_engine)()
        dest_session = sessionmaker(bind=dest_engine)()
        
        # Email utenti Mercury origine
        source_users_query = """
            SELECT email
            FROM users 
            WHERE company_id IN (
                SELECT id FROM companies WHERE name LIKE '%Mercury%'
            ) OR id IN (
                SELECT user_id FROM user_companies uc 
                JOIN companies c ON uc.company_id = c.id 
                WHERE c.name LIKE '%Mercury%'
            )
        """
        
        result = source_session.execute(text(source_users_query))
        source_emails = [row[0] for row in result.fetchall() if row[0]]
        
        # Email utenti destinazione
        dest_users_query = "SELECT email FROM users"
        result = dest_session.execute(text(dest_users_query))
        dest_emails = [row[0] for row in result.fetchall() if row[0]]
        
        # Trova duplicati
        duplicates = set(source_emails) & set(dest_emails)
        
        logger.info(f"📧 Email utenti Mercury origine: {len(source_emails)}")
        logger.info(f"📧 Email utenti destinazione: {len(dest_emails)}")
        logger.info(f"⚠️ Potenziali duplicati: {len(duplicates)}")
        
        if duplicates:
            logger.warning("📋 Email duplicate:")
            for email in list(duplicates)[:10]:  # Mostra prime 10
                logger.warning(f"   - {email}")
            if len(duplicates) > 10:
                logger.warning(f"   ... e altre {len(duplicates) - 10}")
        
        # Guest duplicati
        source_guests_query = """
            SELECT email
            FROM guest_users gu
            WHERE gu.id IN (
                SELECT DISTINCT guest_user_id FROM guest_activities ga
                JOIN documents d ON ga.document_id = d.id
                JOIN companies c ON d.company_id = c.id
                WHERE c.name LIKE '%Mercury%'
            )
        """
        
        result = source_session.execute(text(source_guests_query))
        source_guest_emails = [row[0] for row in result.fetchall() if row[0]]
        
        dest_guests_query = "SELECT email FROM guest_users"
        result = dest_session.execute(text(dest_guests_query))
        dest_guest_emails = [row[0] for row in result.fetchall() if row[0]]
        
        guest_duplicates = set(source_guest_emails) & set(dest_guest_emails)
        
        logger.info(f"📧 Email guest Mercury origine: {len(source_guest_emails)}")
        logger.info(f"📧 Email guest destinazione: {len(dest_guest_emails)}")
        logger.info(f"⚠️ Guest duplicati: {len(guest_duplicates)}")
        
        source_session.close()
        dest_session.close()
        
    except Exception as e:
        logger.error(f"❌ Errore verifica duplicati: {e}")

def main():
    """Funzione principale del test."""
    logger.info("🧪 TEST MIGRAZIONE DOCS MERCURY")
    logger.info("=" * 60)
    
    # Verifica variabili ambiente
    source_url = os.getenv('SOURCE_DB_URL')
    dest_url = os.getenv('DEST_DB_URL')
    
    if not source_url or not dest_url:
        logger.error("❌ Variabili ambiente mancanti!")
        logger.error("Imposta SOURCE_DB_URL e DEST_DB_URL")
        return 1
    
    logger.info(f"📤 Origine: {source_url}")
    logger.info(f"📥 Destinazione: {dest_url}")
    logger.info("=" * 60)
    
    # Test connessioni
    source_ok = test_database_connection(source_url, "ORIGINE")
    dest_ok = test_database_connection(dest_url, "DESTINAZIONE")
    
    if not source_ok or not dest_ok:
        logger.error("❌ Test connessioni fallito!")
        return 1
    
    # Analisi dati
    analyze_source_data(source_url)
    analyze_destination_data(dest_url)
    check_duplicates(source_url, dest_url)
    
    logger.info("=" * 60)
    logger.info("✅ TEST COMPLETATO!")
    logger.info("💡 Per eseguire la migrazione:")
    logger.info("   python scripts/migrazione_docs_mercury.py --dry-run")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 