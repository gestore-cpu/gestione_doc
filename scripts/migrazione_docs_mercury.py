#!/usr/bin/env python3
"""
Script di migrazione dati da DOCS standard a DOCS Mercury.

Trasferisce utenti e guest dal modulo DOCS standard al modulo DOCS Mercury (IP 138.68.80.169).

Uso:
    python scripts/migrazione_docs_mercury.py --dry-run
    python scripts/migrazione_docs_mercury.py
    python scripts/migrazione_docs_mercury.py --overwrite

Variabili ambiente richieste:
    SOURCE_DB_URL: URL database origine (DOCS standard)
    DEST_DB_URL: URL database destinazione (DOCS Mercury)
"""

import os
import sys
import argparse
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
import hashlib
import json

# Aggiungi il path del progetto
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configurazione logging
def setup_logging():
    """Configura il sistema di logging."""
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, 'migrazione_docs_mercury.log')
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger(__name__)

logger = setup_logging()

class DatabaseConnector:
    """Gestisce le connessioni ai database."""
    
    def __init__(self, source_url: str, dest_url: str):
        self.source_url = source_url
        self.dest_url = dest_url
        self.source_engine = None
        self.dest_engine = None
        self.source_session = None
        self.dest_session = None
    
    def connect(self) -> bool:
        """Stabilisce le connessioni ai database."""
        try:
            # Connessione database origine
            self.source_engine = create_engine(self.source_url)
            self.source_session = sessionmaker(bind=self.source_engine)()
            
            # Test connessione origine
            self.source_session.execute(text("SELECT 1"))
            logger.info("✅ Connessione database origine stabilita")
            
            # Connessione database destinazione
            self.dest_engine = create_engine(self.dest_url)
            self.dest_session = sessionmaker(bind=self.dest_engine)()
            
            # Test connessione destinazione
            self.dest_session.execute(text("SELECT 1"))
            logger.info("✅ Connessione database destinazione stabilita")
            
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"❌ Errore connessione database: {e}")
            return False
    
    def close(self):
        """Chiude le connessioni ai database."""
        if self.source_session:
            self.source_session.close()
        if self.dest_session:
            self.dest_session.close()
        logger.info("🔒 Connessioni database chiuse")

class DataMigrator:
    """Gestisce la migrazione dei dati."""
    
    def __init__(self, source_session: Session, dest_session: Session):
        self.source_session = source_session
        self.dest_session = dest_session
        self.stats = {
            'users_imported': 0,
            'users_skipped': 0,
            'users_updated': 0,
            'guests_imported': 0,
            'guests_skipped': 0,
            'guests_updated': 0,
            'errors': []
        }
    
    def get_table_info(self, session: Session, table_name: str) -> Optional[Dict]:
        """Ottiene informazioni sulla struttura di una tabella."""
        try:
            inspector = inspect(session.bind)
            if table_name in inspector.get_table_names():
                columns = inspector.get_columns(table_name)
                return {
                    'exists': True,
                    'columns': [col['name'] for col in columns]
                }
            return {'exists': False, 'columns': []}
        except Exception as e:
            logger.error(f"Errore ottenimento info tabella {table_name}: {e}")
            return None
    
    def check_user_exists(self, email: str) -> bool:
        """Verifica se un utente esiste già nel database destinazione."""
        try:
            result = self.dest_session.execute(
                text("SELECT id FROM users WHERE email = :email"),
                {'email': email}
            )
            return result.fetchone() is not None
        except Exception as e:
            logger.error(f"Errore verifica utente {email}: {e}")
            return False
    
    def check_guest_exists(self, email: str) -> bool:
        """Verifica se un guest esiste già nel database destinazione."""
        try:
            result = self.dest_session.execute(
                text("SELECT id FROM guest_users WHERE email = :email"),
                {'email': email}
            )
            return result.fetchone() is not None
        except Exception as e:
            logger.error(f"Errore verifica guest {email}: {e}")
            return False
    
    def get_mercury_users(self) -> List[Dict]:
        """Recupera gli utenti Mercury dal database origine."""
        try:
            # Query per utenti Mercury (azienda o modulo)
            query = """
                SELECT 
                    id, username, email, password, first_name, last_name,
                    role, company_id, department_id, created_at, last_login,
                    is_active, access_expiration
                FROM users 
                WHERE company_id IN (
                    SELECT id FROM companies WHERE name LIKE '%Mercury%'
                ) OR id IN (
                    SELECT user_id FROM user_companies uc 
                    JOIN companies c ON uc.company_id = c.id 
                    WHERE c.name LIKE '%Mercury%'
                )
            """
            
            result = self.source_session.execute(text(query))
            users = []
            
            for row in result.fetchall():
                user_dict = dict(row._mapping)
                users.append(user_dict)
            
            logger.info(f"📊 Trovati {len(users)} utenti Mercury nel database origine")
            return users
            
        except Exception as e:
            logger.error(f"Errore recupero utenti Mercury: {e}")
            return []
    
    def get_mercury_guests(self) -> List[Dict]:
        """Recupera i guest Mercury dal database origine."""
        try:
            # Query per guest Mercury
            query = """
                SELECT 
                    id, email, password_hash, registered_at, is_active,
                    access_expiration, last_login
                FROM guest_users 
                WHERE id IN (
                    SELECT DISTINCT guest_user_id FROM guest_activities ga
                    JOIN documents d ON ga.document_id = d.id
                    JOIN companies c ON d.company_id = c.id
                    WHERE c.name LIKE '%Mercury%'
                ) OR id IN (
                    SELECT DISTINCT guest_user_id FROM guest_comments gc
                    JOIN documents d ON gc.document_id = d.id
                    JOIN companies c ON d.company_id = c.id
                    WHERE c.name LIKE '%Mercury%'
                )
            """
            
            result = self.source_session.execute(text(query))
            guests = []
            
            for row in result.fetchall():
                guest_dict = dict(row._mapping)
                guests.append(guest_dict)
            
            logger.info(f"📊 Trovati {len(guests)} guest Mercury nel database origine")
            return guests
            
        except Exception as e:
            logger.error(f"Errore recupero guest Mercury: {e}")
            return []
    
    def migrate_user(self, user_data: Dict, dry_run: bool = False, overwrite: bool = False) -> bool:
        """Migra un singolo utente."""
        try:
            email = user_data.get('email')
            if not email:
                logger.warning(f"⚠️ Utente senza email, skip: {user_data.get('username', 'N/A')}")
                return False
            
            # Verifica se esiste già
            exists = self.check_user_exists(email)
            
            if exists and not overwrite:
                logger.info(f"⏭️ Utente già esistente, skip: {email}")
                self.stats['users_skipped'] += 1
                return False
            
            if dry_run:
                logger.info(f"🔍 DRY RUN - Migrerebbe utente: {email}")
                self.stats['users_imported'] += 1
                return True
            
            # Prepara dati per inserimento
            insert_data = {
                'username': user_data.get('username', email.split('@')[0]),
                'email': email,
                'password': user_data.get('password', ''),
                'first_name': user_data.get('first_name', ''),
                'last_name': user_data.get('last_name', ''),
                'role': user_data.get('role', 'user'),
                'can_download': True,
                'created_at': user_data.get('created_at', datetime.utcnow()),
                'access_expiration': user_data.get('access_expiration')
            }
            
            if exists and overwrite:
                # Aggiorna utente esistente
                update_query = """
                    UPDATE users SET 
                        username = :username,
                        first_name = :first_name,
                        last_name = :last_name,
                        role = :role,
                        can_download = :can_download,
                        access_expiration = :access_expiration
                    WHERE email = :email
                """
                self.dest_session.execute(text(update_query), insert_data)
                logger.info(f"🔄 Aggiornato utente: {email}")
                self.stats['users_updated'] += 1
            else:
                # Inserisce nuovo utente
                insert_query = """
                    INSERT INTO users (username, email, password, first_name, last_name, 
                                     role, can_download, created_at, access_expiration)
                    VALUES (:username, :email, :password, :first_name, :last_name,
                           :role, :can_download, :created_at, :access_expiration)
                """
                self.dest_session.execute(text(insert_query), insert_data)
                logger.info(f"✅ Migrato utente: {email}")
                self.stats['users_imported'] += 1
            
            # Registra attività AI post-migrazione
            if not dry_run:
                self._registra_attivita_ai_utente(user_data.get('id'), email)
            
            return True
            
        except Exception as e:
            error_msg = f"Errore migrazione utente {email}: {e}"
            logger.error(error_msg)
            self.stats['errors'].append(error_msg)
            return False
    
    def _registra_attivita_ai_utente(self, user_id: int, email: str):
        """Registra attività AI per un utente migrato."""
        try:
            # Recupera ID utente dal database destinazione
            result = self.dest_session.execute(
                text("SELECT id FROM users WHERE email = :email"),
                {'email': email}
            )
            dest_user_id = result.fetchone()
            
            if dest_user_id:
                # Inserisce record attività AI
                insert_query = """
                    INSERT INTO attivita_ai (user_id, stato_iniziale, note, created_at, updated_at)
                    VALUES (:user_id, 'nuovo_import', :note, :created_at, :updated_at)
                """
                
                note = f"Utente migrato da DOCS standard in data {datetime.utcnow().strftime('%Y-%m-%d')}"
                
                self.dest_session.execute(text(insert_query), {
                    'user_id': dest_user_id[0],
                    'note': note,
                    'created_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow()
                })
                
                logger.info(f"🤖 Registrata attività AI per utente: {email}")
                
        except Exception as e:
            logger.error(f"Errore registrazione attività AI utente {email}: {e}")
    
    def _registra_attivita_ai_guest(self, guest_id: int, email: str):
        """Registra attività AI per un guest migrato."""
        try:
            # Recupera ID guest dal database destinazione
            result = self.dest_session.execute(
                text("SELECT id FROM guest_users WHERE email = :email"),
                {'email': email}
            )
            dest_guest_id = result.fetchone()
            
            if dest_guest_id:
                # Inserisce record attività AI
                insert_query = """
                    INSERT INTO attivita_ai (guest_id, stato_iniziale, note, created_at, updated_at)
                    VALUES (:guest_id, 'nuovo_import', :note, :created_at, :updated_at)
                """
                
                note = f"Guest migrato da DOCS standard in data {datetime.utcnow().strftime('%Y-%m-%d')}"
                
                self.dest_session.execute(text(insert_query), {
                    'guest_id': dest_guest_id[0],
                    'note': note,
                    'created_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow()
                })
                
                logger.info(f"🤖 Registrata attività AI per guest: {email}")
                
        except Exception as e:
            logger.error(f"Errore registrazione attività AI guest {email}: {e}")
    
    def migrate_guest(self, guest_data: Dict, dry_run: bool = False, overwrite: bool = False) -> bool:
        """Migra un singolo guest."""
        try:
            email = guest_data.get('email')
            if not email:
                logger.warning(f"⚠️ Guest senza email, skip: ID {guest_data.get('id', 'N/A')}")
                return False
            
            # Verifica se esiste già
            exists = self.check_guest_exists(email)
            
            if exists and not overwrite:
                logger.info(f"⏭️ Guest già esistente, skip: {email}")
                self.stats['guests_skipped'] += 1
                return False
            
            if dry_run:
                logger.info(f"🔍 DRY RUN - Migrerebbe guest: {email}")
                self.stats['guests_imported'] += 1
                return True
            
            # Prepara dati per inserimento
            insert_data = {
                'email': email,
                'password_hash': guest_data.get('password_hash', ''),
                'registered_at': guest_data.get('registered_at', datetime.utcnow())
            }
            
            if exists and overwrite:
                # Aggiorna guest esistente
                update_query = """
                    UPDATE guest_users SET 
                        password_hash = :password_hash,
                        registered_at = :registered_at
                    WHERE email = :email
                """
                self.dest_session.execute(text(update_query), insert_data)
                logger.info(f"🔄 Aggiornato guest: {email}")
                self.stats['guests_updated'] += 1
            else:
                # Inserisce nuovo guest
                insert_query = """
                    INSERT INTO guest_users (email, password_hash, registered_at)
                    VALUES (:email, :password_hash, :registered_at)
                """
                self.dest_session.execute(text(insert_query), insert_data)
                logger.info(f"✅ Migrato guest: {email}")
                self.stats['guests_imported'] += 1
            
            # Registra attività AI post-migrazione
            if not dry_run:
                self._registra_attivita_ai_guest(guest_data.get('id'), email)
            
            return True
            
        except Exception as e:
            error_msg = f"Errore migrazione guest {email}: {e}"
            logger.error(error_msg)
            self.stats['errors'].append(error_msg)
            return False
    
    def migrate_users(self, dry_run: bool = False, overwrite: bool = False) -> bool:
        """Migra tutti gli utenti Mercury."""
        logger.info("🚀 Inizio migrazione utenti...")
        
        users = self.get_mercury_users()
        if not users:
            logger.warning("⚠️ Nessun utente Mercury trovato")
            return True
        
        success_count = 0
        for user in users:
            if self.migrate_user(user, dry_run, overwrite):
                success_count += 1
        
        logger.info(f"✅ Migrazione utenti completata: {success_count}/{len(users)}")
        return success_count == len(users)
    
    def migrate_guests(self, dry_run: bool = False, overwrite: bool = False) -> bool:
        """Migra tutti i guest Mercury."""
        logger.info("🚀 Inizio migrazione guest...")
        
        guests = self.get_mercury_guests()
        if not guests:
            logger.warning("⚠️ Nessun guest Mercury trovato")
            return True
        
        success_count = 0
        for guest in guests:
            if self.migrate_guest(guest, dry_run, overwrite):
                success_count += 1
        
        logger.info(f"✅ Migrazione guest completata: {success_count}/{len(guests)}")
        return success_count == len(guests)
    
    def print_stats(self):
        """Stampa le statistiche della migrazione."""
        logger.info("📊 STATISTICHE MIGRAZIONE")
        logger.info("=" * 50)
        logger.info(f"👥 Utenti importati: {self.stats['users_imported']}")
        logger.info(f"⏭️ Utenti saltati: {self.stats['users_skipped']}")
        logger.info(f"🔄 Utenti aggiornati: {self.stats['users_updated']}")
        logger.info(f"👤 Guest importati: {self.stats['guests_imported']}")
        logger.info(f"⏭️ Guest saltati: {self.stats['guests_skipped']}")
        logger.info(f"🔄 Guest aggiornati: {self.stats['guests_updated']}")
        
        if self.stats['errors']:
            logger.error("❌ ERRORI:")
            for error in self.stats['errors']:
                logger.error(f"   - {error}")
        
        logger.info("=" * 50)

def validate_environment():
    """Valida le variabili ambiente richieste."""
    required_vars = ['SOURCE_DB_URL', 'DEST_DB_URL']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"❌ Variabili ambiente mancanti: {', '.join(missing_vars)}")
        logger.error("Imposta le variabili ambiente:")
        logger.error("export SOURCE_DB_URL='postgresql://user:pass@host/db'")
        logger.error("export DEST_DB_URL='postgresql://user:pass@host/db'")
        return False
    
    return True

def main():
    """Funzione principale dello script."""
    parser = argparse.ArgumentParser(
        description="Script di migrazione dati da DOCS standard a DOCS Mercury",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esempi:
  python scripts/migrazione_docs_mercury.py --dry-run
  python scripts/migrazione_docs_mercury.py
  python scripts/migrazione_docs_mercury.py --overwrite
        """
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Mostra cosa verrebbe migrato senza scrivere'
    )
    
    parser.add_argument(
        '--overwrite',
        action='store_true',
        help='Aggiorna anche i record già esistenti'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Output dettagliato'
    )
    
    args = parser.parse_args()
    
    # Setup logging verboso se richiesto
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logger.info("🚀 AVVIO SCRIPT MIGRAZIONE DOCS MERCURY")
    logger.info("=" * 60)
    
    # Validazione ambiente
    if not validate_environment():
        sys.exit(1)
    
    # Configurazione
    source_url = os.getenv('SOURCE_DB_URL')
    dest_url = os.getenv('DEST_DB_URL')
    
    logger.info(f"📤 Origine: {source_url}")
    logger.info(f"📥 Destinazione: {dest_url}")
    logger.info(f"🔍 Dry run: {args.dry_run}")
    logger.info(f"🔄 Overwrite: {args.overwrite}")
    logger.info("=" * 60)
    
    # Connessione database
    connector = DatabaseConnector(source_url, dest_url)
    if not connector.connect():
        logger.error("❌ Impossibile stabilire connessioni database")
        sys.exit(1)
    
    try:
        # Inizializza migratore
        migrator = DataMigrator(connector.source_session, connector.dest_session)
        
        # Migrazione utenti
        users_success = migrator.migrate_users(args.dry_run, args.overwrite)
        
        # Migrazione guest
        guests_success = migrator.migrate_guests(args.dry_run, args.overwrite)
        
        # Stampa statistiche
        migrator.print_stats()
        
        # Risultato finale
        if users_success and guests_success:
            logger.info("🎉 MIGRAZIONE COMPLETATA CON SUCCESSO!")
            return 0
        else:
            logger.error("❌ MIGRAZIONE COMPLETATA CON ERRORI!")
            return 1
            
    except Exception as e:
        logger.error(f"❌ Errore durante la migrazione: {e}")
        return 1
    
    finally:
        connector.close()

if __name__ == "__main__":
    sys.exit(main()) 