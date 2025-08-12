#!/usr/bin/env python3
"""
Servizio per il monitoraggio AI post-migrazione.
Rileva comportamenti anomali degli utenti/guest appena importati.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text, func, and_, or_
from models import User, GuestUser, AttivitaAI, AlertAI, DownloadLog, DocumentActivityLog

logger = logging.getLogger(__name__)

class AIMonitoringService:
    """Servizio per il monitoraggio AI post-migrazione."""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def check_download_massivo(self, user_id: int = None, guest_id: int = None) -> Optional[AlertAI]:
        """
        Controlla se un utente/guest ha effettuato download massivo (>20 file) nelle prime 24h.
        
        Args:
            user_id: ID utente
            guest_id: ID guest
            
        Returns:
            AlertAI se rilevato comportamento anomalo
        """
        try:
            # Verifica se è un nuovo import
            attivita = self._get_attivita_ai(user_id, guest_id)
            if not attivita or not attivita.is_nuovo_import:
                return None
            
            # Controlla se è entro 24h dall'import
            if attivita.giorni_da_import > 1:
                return None
            
            # Conta download nelle ultime 24h
            download_count = self._count_downloads_24h(user_id, guest_id)
            
            if download_count > 20:
                # Crea alert
                alert = AlertAI(
                    user_id=user_id,
                    guest_id=guest_id,
                    tipo_alert='download_massivo',
                    descrizione=f'Download massivo rilevato: {download_count} file scaricati nelle prime 24h post-migrazione',
                    ip_address=self._get_last_ip(user_id, guest_id),
                    user_agent=self._get_last_user_agent(user_id, guest_id)
                )
                
                self.db.add(alert)
                self.db.commit()
                
                logger.warning(f"🚨 Alert AI: Download massivo per {'utente' if user_id else 'guest'} {user_id or guest_id}")
                return alert
            
            return None
            
        except Exception as e:
            logger.error(f"Errore controllo download massivo: {e}")
            return None
    
    def check_accessi_falliti(self, user_id: int = None, guest_id: int = None) -> Optional[AlertAI]:
        """
        Controlla se un utente/guest ha >5 tentativi di accesso falliti nelle prime 48h.
        
        Args:
            user_id: ID utente
            guest_id: ID guest
            
        Returns:
            AlertAI se rilevato comportamento anomalo
        """
        try:
            # Verifica se è un nuovo import
            attivita = self._get_attivita_ai(user_id, guest_id)
            if not attivita or not attivita.is_nuovo_import:
                return None
            
            # Controlla se è entro 48h dall'import
            if attivita.giorni_da_import > 2:
                return None
            
            # Conta accessi falliti nelle ultime 48h
            failed_count = self._count_failed_logins_48h(user_id, guest_id)
            
            if failed_count > 5:
                # Crea alert
                alert = AlertAI(
                    user_id=user_id,
                    guest_id=guest_id,
                    tipo_alert='accessi_falliti',
                    descrizione=f'Accessi falliti rilevati: {failed_count} tentativi falliti nelle prime 48h post-migrazione',
                    ip_address=self._get_last_ip(user_id, guest_id),
                    user_agent=self._get_last_user_agent(user_id, guest_id)
                )
                
                self.db.add(alert)
                self.db.commit()
                
                logger.warning(f"🚨 Alert AI: Accessi falliti per {'utente' if user_id else 'guest'} {user_id or guest_id}")
                return alert
            
            return None
            
        except Exception as e:
            logger.error(f"Errore controllo accessi falliti: {e}")
            return None
    
    def check_ip_sospetto(self, user_id: int = None, guest_id: int = None, current_ip: str = None) -> Optional[AlertAI]:
        """
        Controlla se un utente/guest accede da IP sospetto entro 7 giorni.
        
        Args:
            user_id: ID utente
            guest_id: ID guest
            current_ip: IP corrente
            
        Returns:
            AlertAI se rilevato comportamento anomalo
        """
        try:
            # Verifica se è un nuovo import
            attivita = self._get_attivita_ai(user_id, guest_id)
            if not attivita or not attivita.is_nuovo_import:
                return None
            
            # Controlla se è entro 7 giorni dall'import
            if attivita.giorni_da_import > 7:
                return None
            
            if not current_ip:
                return None
            
            # Verifica se l'IP è sospetto
            if self._is_suspicious_ip(current_ip):
                # Crea alert
                alert = AlertAI(
                    user_id=user_id,
                    guest_id=guest_id,
                    tipo_alert='ip_sospetto',
                    descrizione=f'Accesso da IP sospetto rilevato: {current_ip} entro 7 giorni post-migrazione',
                    ip_address=current_ip,
                    user_agent=self._get_last_user_agent(user_id, guest_id)
                )
                
                self.db.add(alert)
                self.db.commit()
                
                logger.warning(f"🚨 Alert AI: IP sospetto per {'utente' if user_id else 'guest'} {user_id or guest_id}: {current_ip}")
                return alert
            
            return None
            
        except Exception as e:
            logger.error(f"Errore controllo IP sospetto: {e}")
            return None
    
    def check_comportamento_anomalo(self, user_id: int = None, guest_id: int = None) -> Optional[AlertAI]:
        """
        Controlla comportamenti anomali generali post-migrazione.
        
        Args:
            user_id: ID utente
            guest_id: ID guest
            
        Returns:
            AlertAI se rilevato comportamento anomalo
        """
        try:
            # Verifica se è un nuovo import
            attivita = self._get_attivita_ai(user_id, guest_id)
            if not attivita or not attivita.is_nuovo_import:
                return None
            
            # Controlla se è entro 30 giorni dall'import
            if attivita.giorni_da_import > 30:
                return None
            
            # Analizza pattern di comportamento
            anomalies = self._detect_behavior_anomalies(user_id, guest_id)
            
            if anomalies:
                # Crea alert
                alert = AlertAI(
                    user_id=user_id,
                    guest_id=guest_id,
                    tipo_alert='comportamento_anomalo',
                    descrizione=f'Comportamento anomalo rilevato: {anomalies}',
                    ip_address=self._get_last_ip(user_id, guest_id),
                    user_agent=self._get_last_user_agent(user_id, guest_id)
                )
                
                self.db.add(alert)
                self.db.commit()
                
                logger.warning(f"🚨 Alert AI: Comportamento anomalo per {'utente' if user_id else 'guest'} {user_id or guest_id}")
                return alert
            
            return None
            
        except Exception as e:
            logger.error(f"Errore controllo comportamento anomalo: {e}")
            return None
    
    def run_all_checks(self, user_id: int = None, guest_id: int = None, current_ip: str = None) -> List[AlertAI]:
        """
        Esegue tutti i controlli AI per un utente/guest.
        
        Args:
            user_id: ID utente
            guest_id: ID guest
            current_ip: IP corrente
            
        Returns:
            Lista di alert generati
        """
        alerts = []
        
        # Controllo download massivo
        alert = self.check_download_massivo(user_id, guest_id)
        if alert:
            alerts.append(alert)
        
        # Controllo accessi falliti
        alert = self.check_accessi_falliti(user_id, guest_id)
        if alert:
            alerts.append(alert)
        
        # Controllo IP sospetto
        alert = self.check_ip_sospetto(user_id, guest_id, current_ip)
        if alert:
            alerts.append(alert)
        
        # Controllo comportamento anomalo
        alert = self.check_comportamento_anomalo(user_id, guest_id)
        if alert:
            alerts.append(alert)
        
        return alerts
    
    def _get_attivita_ai(self, user_id: int = None, guest_id: int = None) -> Optional[AttivitaAI]:
        """Recupera l'attività AI per un utente/guest."""
        try:
            if user_id:
                return self.db.query(AttivitaAI).filter(AttivitaAI.user_id == user_id).first()
            elif guest_id:
                return self.db.query(AttivitaAI).filter(AttivitaAI.guest_id == guest_id).first()
            return None
        except Exception as e:
            logger.error(f"Errore recupero attività AI: {e}")
            return None
    
    def _count_downloads_24h(self, user_id: int = None, guest_id: int = None) -> int:
        """Conta i download nelle ultime 24h."""
        try:
            yesterday = datetime.utcnow() - timedelta(days=1)
            
            if user_id:
                return self.db.query(DownloadLog).filter(
                    and_(
                        DownloadLog.user_id == user_id,
                        DownloadLog.timestamp >= yesterday
                    )
                ).count()
            elif guest_id:
                # Per i guest, controlla le attività guest
                return self.db.query(DocumentActivityLog).filter(
                    and_(
                        DocumentActivityLog.user_id == guest_id,
                        DocumentActivityLog.action == 'download',
                        DocumentActivityLog.timestamp >= yesterday
                    )
                ).count()
            
            return 0
        except Exception as e:
            logger.error(f"Errore conteggio download: {e}")
            return 0
    
    def _count_failed_logins_48h(self, user_id: int = None, guest_id: int = None) -> int:
        """Conta gli accessi falliti nelle ultime 48h."""
        try:
            two_days_ago = datetime.utcnow() - timedelta(days=2)
            
            # Controlla log di accesso fallito
            # Nota: Questo dipende dalla struttura del tuo sistema di logging
            # Adatta la query in base ai tuoi log di autenticazione
            
            return 0  # Placeholder
        except Exception as e:
            logger.error(f"Errore conteggio accessi falliti: {e}")
            return 0
    
    def _is_suspicious_ip(self, ip: str) -> bool:
        """Verifica se un IP è sospetto."""
        try:
            # Lista di IP sospetti (esempi)
            suspicious_ips = [
                '192.168.1.100',  # IP interno sospetto
                '10.0.0.50',      # IP interno sospetto
                # Aggiungi altri IP sospetti
            ]
            
            # Verifica se l'IP è nella lista sospetti
            if ip in suspicious_ips:
                return True
            
            # Verifica se è un IP esterno quando dovrebbe essere interno
            if not ip.startswith(('192.168.', '10.', '172.')):
                return True
            
            return False
        except Exception as e:
            logger.error(f"Errore verifica IP sospetto: {e}")
            return False
    
    def _detect_behavior_anomalies(self, user_id: int = None, guest_id: int = None) -> str:
        """Rileva anomalie nel comportamento."""
        try:
            anomalies = []
            
            # Controlla orari di accesso insoliti
            if self._has_unusual_access_times(user_id, guest_id):
                anomalies.append("Orari di accesso insoliti")
            
            # Controlla pattern di navigazione anomali
            if self._has_anomalous_navigation(user_id, guest_id):
                anomalies.append("Pattern di navigazione anomali")
            
            # Controlla tentativi di accesso a documenti riservati
            if self._has_restricted_document_access(user_id, guest_id):
                anomalies.append("Tentativi di accesso a documenti riservati")
            
            return "; ".join(anomalies) if anomalies else ""
        except Exception as e:
            logger.error(f"Errore rilevamento anomalie comportamento: {e}")
            return ""
    
    def _has_unusual_access_times(self, user_id: int = None, guest_id: int = None) -> bool:
        """Verifica se ci sono accessi in orari insoliti."""
        try:
            # Controlla accessi tra le 23:00 e le 06:00
            # Implementa la logica specifica per il tuo sistema
            return False  # Placeholder
        except Exception as e:
            logger.error(f"Errore verifica orari accesso: {e}")
            return False
    
    def _has_anomalous_navigation(self, user_id: int = None, guest_id: int = None) -> bool:
        """Verifica se ci sono pattern di navigazione anomali."""
        try:
            # Implementa la logica per rilevare navigazione anomala
            return False  # Placeholder
        except Exception as e:
            logger.error(f"Errore verifica navigazione anomala: {e}")
            return False
    
    def _has_restricted_document_access(self, user_id: int = None, guest_id: int = None) -> bool:
        """Verifica se ci sono tentativi di accesso a documenti riservati."""
        try:
            # Implementa la logica per rilevare accessi a documenti riservati
            return False  # Placeholder
        except Exception as e:
            logger.error(f"Errore verifica accessi documenti riservati: {e}")
            return False
    
    def _get_last_ip(self, user_id: int = None, guest_id: int = None) -> Optional[str]:
        """Recupera l'ultimo IP utilizzato."""
        try:
            # Implementa la logica per recuperare l'ultimo IP
            return None  # Placeholder
        except Exception as e:
            logger.error(f"Errore recupero ultimo IP: {e}")
            return None
    
    def _get_last_user_agent(self, user_id: int = None, guest_id: int = None) -> Optional[str]:
        """Recupera l'ultimo user agent utilizzato."""
        try:
            # Implementa la logica per recuperare l'ultimo user agent
            return None  # Placeholder
        except Exception as e:
            logger.error(f"Errore recupero ultimo user agent: {e}")
            return None


def genera_alert_ai_post_import(user_id: int = None, guest_id: int = None, current_ip: str = None) -> List[Dict]:
    """
    Genera alert AI per utenti/guest post-migrazione.
    
    Args:
        user_id: ID utente
        guest_id: ID guest
        current_ip: IP corrente
        
    Returns:
        Lista di alert generati
    """
    try:
        from database import get_db
        
        db = get_db()
        monitoring_service = AIMonitoringService(db)
        
        alerts = monitoring_service.run_all_checks(user_id, guest_id, current_ip)
        
        results = []
        for alert in alerts:
            results.append({
                'id': alert.id,
                'tipo_alert': alert.tipo_alert,
                'descrizione': alert.descrizione,
                'stato': alert.stato,
                'timestamp': alert.timestamp.isoformat(),
                'ip_address': alert.ip_address
            })
        
        return results
        
    except Exception as e:
        logger.error(f"Errore generazione alert AI post-import: {e}")
        return [] 