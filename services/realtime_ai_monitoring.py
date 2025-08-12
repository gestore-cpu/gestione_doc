#!/usr/bin/env python3
"""
Servizio per il monitoraggio AI in tempo reale.
Analizza continuamente le attività degli utenti e genera alert immediati.
"""

import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text, func, and_, or_, desc
from models import User, GuestUser, AlertAI, DownloadLog, DocumentActivityLog, DocumentReadLog, AdminLog, db

logger = logging.getLogger(__name__)

class RealtimeAIMonitoring:
    """Servizio per il monitoraggio AI in tempo reale."""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.working_hours = {
            'start': 6,  # 06:00
            'end': 22    # 22:00
        }
    
    def analizza_attivita_realtime(self) -> List[AlertAI]:
        """
        Analizza tutte le attività in tempo reale e genera alert.
        
        Returns:
            Lista di alert generati
        """
        alerts = []
        
        try:
            # 1. Controllo accessi fuori orario
            alerts.extend(self._check_accessi_fuori_orario())
            
            # 2. Controllo download massivi
            alerts.extend(self._check_download_massivi())
            
            # 3. Controllo errori login ripetuti
            alerts.extend(self._check_errori_login_ripetuti())
            
            # 4. Controllo IP insoliti
            alerts.extend(self._check_ip_insoliti())
            
            # 5. Controllo accessi simultanei
            alerts.extend(self._check_accessi_simultanei())
            
            # 6. Controllo accessi non autorizzati
            alerts.extend(self._check_accessi_non_autorizzati())
            
            logger.info(f"🤖 Analisi tempo reale completata: {len(alerts)} alert generati")
            return alerts
            
        except Exception as e:
            logger.error(f"Errore analisi tempo reale: {e}")
            return []
    
    def _check_accessi_fuori_orario(self) -> List[AlertAI]:
        """Controlla accessi fuori orario lavorativo."""
        alerts = []
        
        try:
            now = datetime.utcnow()
            current_hour = now.hour
            
            # Verifica se siamo fuori orario lavorativo
            if current_hour < self.working_hours['start'] or current_hour >= self.working_hours['end']:
                # Cerca accessi recenti (ultimi 30 minuti)
                recent_accesses = self.db.query(DocumentReadLog).filter(
                    and_(
                        DocumentReadLog.timestamp >= now - timedelta(minutes=30),
                        DocumentReadLog.timestamp <= now
                    )
                ).all()
                
                for access in recent_accesses:
                    # Crea alert per accesso fuori orario
                    alert = AlertAI(
                        user_id=access.user_id,
                        tipo_alert='accesso_fuori_orario',
                        descrizione=f'Accesso rilevato alle {access.timestamp.strftime("%H:%M")} fuori orario lavorativo',
                        livello='medio',
                        ip_address=access.ip_address,
                        user_agent=access.user_agent,
                        timestamp=now
                    )
                    
                    self.db.add(alert)
                    alerts.append(alert)
                    logger.warning(f"🚨 Alert accesso fuori orario per utente {access.user_id}")
            
            return alerts
            
        except Exception as e:
            logger.error(f"Errore controllo accessi fuori orario: {e}")
            return []
    
    def _check_download_massivi(self) -> List[AlertAI]:
        """Controlla download massivi (>50 file in 1 ora)."""
        alerts = []
        
        try:
            now = datetime.utcnow()
            one_hour_ago = now - timedelta(hours=1)
            
            # Conta download per utente nell'ultima ora
            download_counts = self.db.query(
                DownloadLog.user_id,
                func.count(DownloadLog.id).label('count')
            ).filter(
                DownloadLog.timestamp >= one_hour_ago
            ).group_by(DownloadLog.user_id).all()
            
            for user_id, count in download_counts:
                if count > 50:
                    # Crea alert per download massivo
                    alert = AlertAI(
                        user_id=user_id,
                        tipo_alert='download_massivo',
                        descrizione=f'Download massivo rilevato: {count} file scaricati nell\'ultima ora',
                        livello='alto',
                        timestamp=now
                    )
                    
                    self.db.add(alert)
                    alerts.append(alert)
                    logger.warning(f"🚨 Alert download massivo per utente {user_id}: {count} file")
            
            return alerts
            
        except Exception as e:
            logger.error(f"Errore controllo download massivi: {e}")
            return []
    
    def _check_errori_login_ripetuti(self) -> List[AlertAI]:
        """Controlla errori di login ripetuti (>10 in 30 minuti)."""
        alerts = []
        
        try:
            now = datetime.utcnow()
            thirty_minutes_ago = now - timedelta(minutes=30)
            
            # Conta errori di login per IP negli ultimi 30 minuti
            # Nota: Questo dipende dalla struttura del tuo sistema di logging
            # Adatta la query in base ai tuoi log di autenticazione
            
            # Esempio con AdminLog (se usi per loggare errori login)
            error_counts = self.db.query(
                AdminLog.performed_by,
                func.count(AdminLog.id).label('count')
            ).filter(
                and_(
                    AdminLog.action.like('%login_failed%'),
                    AdminLog.timestamp >= thirty_minutes_ago
                )
            ).group_by(AdminLog.performed_by).all()
            
            for user_email, count in error_counts:
                if count > 10:
                    # Trova user_id dall'email
                    user = self.db.query(User).filter(User.email == user_email).first()
                    if user:
                        alert = AlertAI(
                            user_id=user.id,
                            tipo_alert='accessi_falliti',
                            descrizione=f'Errori login ripetuti: {count} tentativi falliti negli ultimi 30 minuti',
                            livello='alto',
                            timestamp=now
                        )
                        
                        self.db.add(alert)
                        alerts.append(alert)
                        logger.warning(f"🚨 Alert errori login per utente {user.id}: {count} tentativi")
            
            return alerts
            
        except Exception as e:
            logger.error(f"Errore controllo errori login: {e}")
            return []
    
    def _check_ip_insoliti(self) -> List[AlertAI]:
        """Controlla accessi da IP mai visti prima per l'utente."""
        alerts = []
        
        try:
            now = datetime.utcnow()
            recent_accesses = self.db.query(DocumentReadLog).filter(
                DocumentReadLog.timestamp >= now - timedelta(hours=1)
            ).all()
            
            for access in recent_accesses:
                if not access.ip_address:
                    continue
                
                # Verifica se questo IP è insolito per l'utente
                if self._is_ip_insolito(access.user_id, access.ip_address):
                    alert = AlertAI(
                        user_id=access.user_id,
                        tipo_alert='ip_sospetto',
                        descrizione=f'Accesso da IP insolito: {access.ip_address}',
                        livello='medio',
                        ip_address=access.ip_address,
                        user_agent=access.user_agent,
                        timestamp=now
                    )
                    
                    self.db.add(alert)
                    alerts.append(alert)
                    logger.warning(f"🚨 Alert IP insolito per utente {access.user_id}: {access.ip_address}")
            
            return alerts
            
        except Exception as e:
            logger.error(f"Errore controllo IP insoliti: {e}")
            return []
    
    def _check_accessi_simultanei(self) -> List[AlertAI]:
        """Controlla accessi simultanei da IP diversi in meno di 5 minuti."""
        alerts = []
        
        try:
            now = datetime.utcnow()
            five_minutes_ago = now - timedelta(minutes=5)
            
            # Raggruppa accessi per utente e IP
            recent_accesses = self.db.query(DocumentReadLog).filter(
                DocumentReadLog.timestamp >= five_minutes_ago
            ).all()
            
            # Raggruppa per utente
            user_accesses = {}
            for access in recent_accesses:
                if access.user_id not in user_accesses:
                    user_accesses[access.user_id] = []
                user_accesses[access.user_id].append(access)
            
            # Verifica accessi simultanei
            for user_id, accesses in user_accesses.items():
                unique_ips = set(access.ip_address for access in accesses if access.ip_address)
                
                if len(unique_ips) > 1:
                    alert = AlertAI(
                        user_id=user_id,
                        tipo_alert='accesso_simultaneo',
                        descrizione=f'Accesso simultaneo da {len(unique_ips)} IP diversi: {", ".join(unique_ips)}',
                        livello='alto',
                        ip_address=list(unique_ips)[0],
                        timestamp=now
                    )
                    
                    self.db.add(alert)
                    alerts.append(alert)
                    logger.warning(f"🚨 Alert accesso simultaneo per utente {user_id}: {len(unique_ips)} IP")
            
            return alerts
            
        except Exception as e:
            logger.error(f"Errore controllo accessi simultanei: {e}")
            return []
    
    def _check_accessi_non_autorizzati(self) -> List[AlertAI]:
        """Controlla tentativi di accesso a documenti non autorizzati."""
        alerts = []
        
        try:
            now = datetime.utcnow()
            
            # Cerca tentativi di accesso negato
            denied_accesses = self.db.query(DocumentActivityLog).filter(
                and_(
                    DocumentActivityLog.action == 'access_denied',
                    DocumentActivityLog.timestamp >= now - timedelta(hours=1)
                )
            ).all()
            
            for access in denied_accesses:
                alert = AlertAI(
                    user_id=access.user_id,
                    tipo_alert='accesso_non_autorizzato',
                    descrizione=f'Tentativo di accesso non autorizzato al documento {access.document_id}',
                    livello='critico',
                    timestamp=now
                )
                
                self.db.add(alert)
                alerts.append(alert)
                logger.warning(f"🚨 Alert accesso non autorizzato per utente {access.user_id}")
            
            return alerts
            
        except Exception as e:
            logger.error(f"Errore controllo accessi non autorizzati: {e}")
            return []
    
    def _is_ip_insolito(self, user_id: int, ip_address: str) -> bool:
        """Verifica se un IP è insolito per un utente."""
        try:
            # Recupera tutti gli IP utilizzati dall'utente negli ultimi 30 giorni
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            
            user_ips = self.db.query(DocumentReadLog.ip_address).filter(
                and_(
                    DocumentReadLog.user_id == user_id,
                    DocumentReadLog.timestamp >= thirty_days_ago,
                    DocumentReadLog.ip_address.isnot(None)
                )
            ).distinct().all()
            
            known_ips = [ip[0] for ip in user_ips if ip[0]]
            
            # Se l'IP non è mai stato visto prima, è insolito
            return ip_address not in known_ips
            
        except Exception as e:
            logger.error(f"Errore verifica IP insolito: {e}")
            return False
    
    def get_geolocation_info(self, ip_address: str) -> Optional[Dict]:
        """Recupera informazioni di geolocalizzazione per un IP."""
        try:
            # Usa ipapi.co per geolocalizzazione
            response = requests.get(f'https://ipapi.co/{ip_address}/json/', timeout=5)
            if response.status_code == 200:
                data = response.json()
                return {
                    'country': data.get('country_name'),
                    'city': data.get('city'),
                    'region': data.get('region'),
                    'timezone': data.get('timezone'),
                    'org': data.get('org')
                }
        except Exception as e:
            logger.error(f"Errore geolocalizzazione IP {ip_address}: {e}")
        
        return None
    
    def send_ceo_notification(self, alert: AlertAI) -> bool:
        """Invia notifica al CEO per alert di livello alto o critico."""
        try:
            if alert.livello in ['alto', 'critico']:
                # Implementa l'invio email al CEO
                # Per ora logghiamo solo
                logger.info(f"📧 Notifica CEO per alert {alert.id}: {alert.descrizione}")
                return True
        except Exception as e:
            logger.error(f"Errore invio notifica CEO: {e}")
        
        return False
    
    def create_dashboard_notification(self, alert: AlertAI) -> bool:
        """Crea notifica per la dashboard admin."""
        try:
            # Implementa notifica toast per dashboard
            # Per ora logghiamo solo
            logger.info(f"🔔 Notifica dashboard per alert {alert.id}: {alert.descrizione}")
            return True
        except Exception as e:
            logger.error(f"Errore creazione notifica dashboard: {e}")
        
        return False


def analizza_attivita_realtime() -> List[Dict]:
    """
    Funzione principale per analizzare attività in tempo reale.
    
    Returns:
        Lista di alert generati in formato dizionario
    """
    try:
        from database import get_db
        
        db = get_db()
        monitoring = RealtimeAIMonitoring(db)
        
        alerts = monitoring.analizza_attivita_realtime()
        
        results = []
        for alert in alerts:
            # Salva alert nel database
            db.session.commit()
            
            # Invia notifiche
            monitoring.send_ceo_notification(alert)
            monitoring.create_dashboard_notification(alert)
            
            results.append({
                'id': alert.id,
                'tipo_alert': alert.tipo_alert,
                'livello': alert.livello,
                'descrizione': alert.descrizione,
                'user_id': alert.user_id,
                'guest_id': alert.guest_id,
                'timestamp': alert.timestamp.isoformat()
            })
        
        return results
        
    except Exception as e:
        logger.error(f"Errore analisi attività tempo reale: {e}")
        return [] 