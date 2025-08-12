"""
Servizio per integrazione antivirus e calcolo hash dei file.
Gestisce scansioni ClamAV e calcolo hash SHA-256.
"""

import hashlib
import logging
import os
import socket
import tempfile
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from pathlib import Path

import pyclamd
from flask import current_app
from extensions import db
from models import FileHash, AntivirusScan, AntivirusVerdict

logger = logging.getLogger(__name__)


class AntivirusService:
    """
    Servizio per gestione antivirus e hash dei file.
    """
    
    def __init__(self):
        """Inizializza il servizio antivirus."""
        self.clamav_host = os.getenv('CLAMAV_HOST', 'localhost')
        self.clamav_port = int(os.getenv('CLAMAV_PORT', 3310))
        self.strict_mode = os.getenv('STRICT_UPLOAD_SECURITY', 'False').lower() == 'true'
        self._connection = None
    
    def _get_clamav_connection(self) -> Optional[pyclamd.ClamdAgnostic]:
        """
        Ottiene una connessione a ClamAV.
        
        Returns:
            Optional[pyclamd.ClamdAgnostic]: Connessione ClamAV o None se fallita
        """
        try:
            # Prima prova connessione socket Unix (più veloce)
            if os.path.exists('/var/run/clamav/clamd.ctl'):
                cd = pyclamd.ClamdUnixSocket('/var/run/clamav/clamd.ctl')
                if cd.ping():
                    return cd
            
            # Fallback a connessione TCP
            cd = pyclamd.ClamdNetworkSocket(host=self.clamav_host, port=self.clamav_port)
            if cd.ping():
                return cd
                
            return None
            
        except Exception as e:
            logger.warning(f"Impossibile connettersi a ClamAV: {e}")
            return None
    
    def calculate_sha256(self, file_path: str) -> str:
        """
        Calcola l'hash SHA-256 di un file.
        
        Args:
            file_path: Percorso del file
            
        Returns:
            str: Hash SHA-256 in formato esadecimale
            
        Raises:
            IOError: Se il file non può essere letto
        """
        sha256_hash = hashlib.sha256()
        
        try:
            with open(file_path, "rb") as f:
                # Leggi il file a blocchi per gestire file grandi
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            
            return sha256_hash.hexdigest()
            
        except IOError as e:
            logger.error(f"Errore calcolo hash per {file_path}: {e}")
            raise
    
    def scan_file_content(self, file_content: bytes) -> Dict[str, Any]:
        """
        Scansiona il contenuto di un file con ClamAV.
        
        Args:
            file_content: Contenuto del file in bytes
            
        Returns:
            Dict: Risultato della scansione con keys:
                  - verdict: 'clean' | 'infected' | 'error'
                  - details: dettagli aggiuntivi
                  - engine: versione engine
                  - signature: versione signature
        """
        try:
            cd = self._get_clamav_connection()
            
            if not cd:
                logger.warning("ClamAV non disponibile")
                return {
                    'verdict': 'error',
                    'details': 'ClamAV service unavailable',
                    'engine': 'unknown',
                    'signature': 'unknown'
                }
            
            # Ottieni informazioni versione
            try:
                version_info = cd.version()
                engine_version = version_info.split('/')[0] if version_info else 'unknown'
                signature_version = version_info.split('/')[1] if '/' in version_info else 'unknown'
            except:
                engine_version = 'unknown'
                signature_version = 'unknown'
            
            # Scansiona il contenuto
            scan_result = cd.scan_stream(file_content)
            
            if scan_result is None:
                # File pulito
                return {
                    'verdict': 'clean',
                    'details': 'No threats detected',
                    'engine': engine_version,
                    'signature': signature_version
                }
            else:
                # File infetto
                threat_name = scan_result.get('stream', 'Unknown threat')
                return {
                    'verdict': 'infected',
                    'details': f'Threat detected: {threat_name}',
                    'engine': engine_version,
                    'signature': signature_version
                }
                
        except Exception as e:
            logger.error(f"Errore scansione ClamAV: {e}")
            return {
                'verdict': 'error',
                'details': f'Scan error: {str(e)}',
                'engine': 'unknown',
                'signature': 'unknown'
            }
    
    def scan_file_path(self, file_path: str) -> Dict[str, Any]:
        """
        Scansiona un file dal percorso con ClamAV.
        
        Args:
            file_path: Percorso del file
            
        Returns:
            Dict: Risultato della scansione
        """
        try:
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            return self.scan_file_content(file_content)
            
        except IOError as e:
            logger.error(f"Errore lettura file {file_path}: {e}")
            return {
                'verdict': 'error',
                'details': f'File read error: {str(e)}',
                'engine': 'unknown',
                'signature': 'unknown'
            }
    
    def save_file_hash(self, file_id: int, file_path: str) -> bool:
        """
        Calcola e salva l'hash SHA-256 di un file nel database.
        
        Args:
            file_id: ID del file nel database
            file_path: Percorso del file
            
        Returns:
            bool: True se salvato con successo
        """
        try:
            hash_value = self.calculate_sha256(file_path)
            
            # Controlla se esiste già un hash per questo file
            existing_hash = FileHash.query.filter_by(file_id=file_id).first()
            
            if existing_hash:
                # Aggiorna hash esistente
                existing_hash.value = hash_value
                existing_hash.created_at = datetime.utcnow()
            else:
                # Crea nuovo record hash
                file_hash = FileHash(
                    file_id=file_id,
                    algo='SHA256',
                    value=hash_value
                )
                db.session.add(file_hash)
            
            db.session.commit()
            logger.info(f"Hash SHA-256 salvato per file {file_id}: {hash_value}")
            return True
            
        except Exception as e:
            logger.error(f"Errore salvataggio hash per file {file_id}: {e}")
            db.session.rollback()
            return False
    
    def save_antivirus_scan(self, file_id: int, scan_result: Dict[str, Any]) -> bool:
        """
        Salva il risultato della scansione antivirus nel database.
        
        Args:
            file_id: ID del file nel database
            scan_result: Risultato della scansione
            
        Returns:
            bool: True se salvato con successo
        """
        try:
            verdict = AntivirusVerdict.CLEAN if scan_result['verdict'] == 'clean' else AntivirusVerdict.INFECTED
            
            antivirus_scan = AntivirusScan(
                file_id=file_id,
                engine=scan_result.get('engine', 'unknown'),
                signature=scan_result.get('signature', 'unknown'),
                verdict=verdict
            )
            
            db.session.add(antivirus_scan)
            db.session.commit()
            
            logger.info(f"Risultato scansione antivirus salvato per file {file_id}: {scan_result['verdict']}")
            return True
            
        except Exception as e:
            logger.error(f"Errore salvataggio scansione antivirus per file {file_id}: {e}")
            db.session.rollback()
            return False
    
    def process_uploaded_file(self, file_path: str, file_id: int) -> Tuple[bool, Dict[str, Any]]:
        """
        Processa un file appena caricato: calcola hash e scansiona con antivirus.
        
        Args:
            file_path: Percorso del file caricato
            file_id: ID del file nel database
            
        Returns:
            Tuple[bool, Dict]: (success, scan_result)
                success: True se il file è sicuro e può essere conservato
                scan_result: Dettagli della scansione
        """
        try:
            # 1. Calcola e salva hash SHA-256
            hash_saved = self.save_file_hash(file_id, file_path)
            if not hash_saved:
                logger.warning(f"Impossibile salvare hash per file {file_id}")
            
            # 2. Scansiona con antivirus
            scan_result = self.scan_file_path(file_path)
            
            # 3. Salva risultato scansione
            scan_saved = self.save_antivirus_scan(file_id, scan_result)
            if not scan_saved:
                logger.warning(f"Impossibile salvare risultato scansione per file {file_id}")
            
            # 4. Determina se il file è sicuro
            if scan_result['verdict'] == 'infected':
                logger.warning(f"File {file_id} infetto: {scan_result['details']}")
                return False, scan_result
            
            elif scan_result['verdict'] == 'error':
                if self.strict_mode:
                    logger.warning(f"Modalità strict: rifiuto file {file_id} per errore scansione")
                    return False, scan_result
                else:
                    logger.warning(f"Errore scansione file {file_id}, ma modalità permissiva attiva")
                    return True, scan_result
            
            else:  # clean
                logger.info(f"File {file_id} scansionato e risultato pulito")
                return True, scan_result
            
        except Exception as e:
            logger.error(f"Errore processamento file {file_id}: {e}")
            error_result = {
                'verdict': 'error',
                'details': f'Processing error: {str(e)}',
                'engine': 'unknown',
                'signature': 'unknown'
            }
            
            if self.strict_mode:
                return False, error_result
            else:
                return True, error_result
    
    def get_file_security_info(self, file_id: int) -> Dict[str, Any]:
        """
        Ottiene informazioni di sicurezza per un file.
        
        Args:
            file_id: ID del file
            
        Returns:
            Dict: Informazioni di sicurezza con hash e scansioni
        """
        try:
            # Ottieni hash
            file_hash = FileHash.query.filter_by(file_id=file_id).first()
            
            # Ottieni scansioni antivirus (più recente prima)
            scans = AntivirusScan.query.filter_by(file_id=file_id)\
                                     .order_by(AntivirusScan.ts.desc())\
                                     .all()
            
            return {
                'file_id': file_id,
                'hash': {
                    'algorithm': file_hash.algo if file_hash else None,
                    'value': file_hash.value if file_hash else None,
                    'created_at': file_hash.created_at.isoformat() if file_hash else None
                },
                'antivirus_scans': [
                    {
                        'id': scan.id,
                        'engine': scan.engine,
                        'signature': scan.signature,
                        'verdict': scan.verdict.value,
                        'timestamp': scan.ts.isoformat()
                    }
                    for scan in scans
                ],
                'is_safe': len(scans) > 0 and scans[0].verdict == AntivirusVerdict.CLEAN,
                'last_scan': scans[0].ts.isoformat() if scans else None
            }
            
        except Exception as e:
            logger.error(f"Errore recupero informazioni sicurezza per file {file_id}: {e}")
            return {
                'file_id': file_id,
                'hash': None,
                'antivirus_scans': [],
                'is_safe': False,
                'last_scan': None,
                'error': str(e)
            }


# Istanza globale del servizio
antivirus_service = AntivirusService()
