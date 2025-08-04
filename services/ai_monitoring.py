"""
Servizio AI per monitoraggio comportamenti sospetti nei download documentali.
Implementa il sistema di alert automatici per sicurezza e compliance (NIS2, ISO 27001).
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from sqlalchemy import and_, func, desc
from sqlalchemy.orm import Session
from flask import current_app
import requests
import json

from models import db, AIAlert, DownloadLog, DocumentActivityLog, User, Document
from services.ai import get_ai_response

logger = logging.getLogger(__name__)

class AIMonitoringService:
    """
    Servizio per il monitoraggio AI dei comportamenti sospetti nei download.
    """
    
    def __init__(self):
        self.suspicious_patterns = {
            'download_massivo': {
                'threshold': 5,  # >5 download
                'timeframe': 2,  # in <2 minuti
                'severity': 'alta'
            },
            'accesso_fuori_orario': {
                'start_hour': 20,  # 20:00
                'end_hour': 7,     # 07:00
                'severity': 'media'
            },
            'ripetizione_file': {
                'threshold': 3,  # >3 volte
                'timeframe': 5,  # in 5 minuti
                'severity': 'media'
            },
            'ip_sospetto': {
                'severity': 'alta'
            }
        }
    
    def analizza_download_sospetti(self) -> List[Dict]:
        """
        Analizza i log di download per identificare comportamenti sospetti.
        
        Returns:
            List[Dict]: Lista di alert generati
        """
        try:
            alerts = []
            
            # 1. Analisi download multipli in breve tempo
            alerts.extend(self._check_massive_downloads())
            
            # 2. Analisi accessi fuori orario
            alerts.extend(self._check_off_hours_access())
            
            # 3. Analisi ripetizione file
            alerts.extend(self._check_file_repetition())
            
            # 4. Analisi IP sospetti
            alerts.extend(self._check_suspicious_ips())
            
            # 5. Analisi tentativi su documenti bloccati
            alerts.extend(self._check_blocked_document_attempts())
            
            logger.info(f"Analisi completata: {len(alerts)} alert generati")
            return alerts
            
        except Exception as e:
            logger.error(f"Errore durante analisi download sospetti: {e}")
            return []
    
    def _check_massive_downloads(self) -> List[Dict]:
        """
        Identifica download multipli (>5) in breve tempo (<2 minuti) dallo stesso utente.
        """
        alerts = []
        
        try:
            # Query per trovare utenti con >5 download in <2 minuti
            recent_downloads = db.session.query(
                DownloadLog.user_id,
                func.count(DownloadLog.id).label('download_count'),
                func.min(DownloadLog.timestamp).label('first_download'),
                func.max(DownloadLog.timestamp).label('last_download')
            ).filter(
                DownloadLog.timestamp >= datetime.utcnow() - timedelta(hours=1)
            ).group_by(DownloadLog.user_id).having(
                func.count(DownloadLog.id) >= self.suspicious_patterns['download_massivo']['threshold']
            ).all()
            
            for user_id, count, first_dl, last_dl in recent_downloads:
                time_diff = (last_dl - first_dl).total_seconds() / 60
                
                if time_diff <= self.suspicious_patterns['download_massivo']['timeframe']:
                    user = User.query.get(user_id)
                    if user:
                        alert = {
                            'alert_type': 'download_massivo',
                            'user_id': user_id,
                            'severity': self.suspicious_patterns['download_massivo']['severity'],
                            'description': f"Utente {user.username} ha scaricato {count} documenti in {time_diff:.1f} minuti",
                            'details': {
                                'download_count': count,
                                'timeframe_minutes': time_diff,
                                'first_download': first_dl.isoformat(),
                                'last_download': last_dl.isoformat()
                            }
                        }
                        alerts.append(alert)
                        
        except Exception as e:
            logger.error(f"Errore durante controllo download massivi: {e}")
        
        return alerts
    
    def _check_off_hours_access(self) -> List[Dict]:
        """
        Identifica accessi fuori orario lavorativo (20:00-07:00).
        """
        alerts = []
        
        try:
            current_hour = datetime.utcnow().hour
            is_off_hours = (
                current_hour >= self.suspicious_patterns['accesso_fuori_orario']['start_hour'] or
                current_hour <= self.suspicious_patterns['accesso_fuori_orario']['end_hour']
            )
            
            if is_off_hours:
                # Trova download nelle ultime ore fuori orario
                off_hours_downloads = DownloadLog.query.filter(
                    and_(
                        DownloadLog.timestamp >= datetime.utcnow() - timedelta(hours=12),
                        func.extract('hour', DownloadLog.timestamp) >= self.suspicious_patterns['accesso_fuori_orario']['start_hour']
                    )
                ).all()
                
                for download in off_hours_downloads:
                    user = User.query.get(download.user_id)
                    if user:
                        alert = {
                            'alert_type': 'accesso_fuori_orario',
                            'user_id': download.user_id,
                            'document_id': download.document_id,
                            'severity': self.suspicious_patterns['accesso_fuori_orario']['severity'],
                            'description': f"Accesso fuori orario da {user.username} alle {download.timestamp.strftime('%H:%M')}",
                            'details': {
                                'access_time': download.timestamp.isoformat(),
                                'hour': download.timestamp.hour
                            }
                        }
                        alerts.append(alert)
                        
        except Exception as e:
            logger.error(f"Errore durante controllo accessi fuori orario: {e}")
        
        return alerts
    
    def _check_file_repetition(self) -> List[Dict]:
        """
        Identifica ripetizioni dello stesso file (>3 volte in 5 minuti).
        """
        alerts = []
        
        try:
            # Query per trovare ripetizioni dello stesso documento
            recent_downloads = DownloadLog.query.filter(
                DownloadLog.timestamp >= datetime.utcnow() - timedelta(minutes=10)
            ).order_by(DownloadLog.user_id, DownloadLog.document_id, DownloadLog.timestamp).all()
            
            # Raggruppa per utente e documento
            user_doc_downloads = {}
            for download in recent_downloads:
                key = (download.user_id, download.document_id)
                if key not in user_doc_downloads:
                    user_doc_downloads[key] = []
                user_doc_downloads[key].append(download)
            
            # Controlla ripetizioni
            for (user_id, doc_id), downloads in user_doc_downloads.items():
                if len(downloads) >= self.suspicious_patterns['ripetizione_file']['threshold']:
                    time_diff = (downloads[-1].timestamp - downloads[0].timestamp).total_seconds() / 60
                    
                    if time_diff <= self.suspicious_patterns['ripetizione_file']['timeframe']:
                        user = User.query.get(user_id)
                        document = Document.query.get(doc_id)
                        
                        if user and document:
                            alert = {
                                'alert_type': 'ripetizione_file',
                                'user_id': user_id,
                                'document_id': doc_id,
                                'severity': self.suspicious_patterns['ripetizione_file']['severity'],
                                'description': f"Utente {user.username} ha scaricato '{document.title}' {len(downloads)} volte in {time_diff:.1f} minuti",
                                'details': {
                                    'download_count': len(downloads),
                                    'timeframe_minutes': time_diff,
                                    'document_title': document.title
                                }
                            }
                            alerts.append(alert)
                            
        except Exception as e:
            logger.error(f"Errore durante controllo ripetizione file: {e}")
        
        return alerts
    
    def _check_suspicious_ips(self) -> List[Dict]:
        """
        Identifica accessi da IP sospetti o non aziendali.
        """
        alerts = []
        
        try:
            # Lista IP aziendali autorizzati (da configurare)
            authorized_ips = current_app.config.get('AUTHORIZED_IPS', [])
            
            # Per ora, controlliamo solo se ci sono IP registrati
            # In futuro, si può implementare geolocalizzazione
            recent_activities = DocumentActivityLog.query.filter(
                DocumentActivityLog.timestamp >= datetime.utcnow() - timedelta(hours=1)
            ).all()
            
            for activity in recent_activities:
                # Se l'IP non è nella lista autorizzata
                if hasattr(activity, 'ip_address') and activity.ip_address:
                    if activity.ip_address not in authorized_ips:
                        user = User.query.get(activity.user_id)
                        if user:
                            alert = {
                                'alert_type': 'ip_sospetto',
                                'user_id': activity.user_id,
                                'document_id': activity.document_id,
                                'severity': self.suspicious_patterns['ip_sospetto']['severity'],
                                'description': f"Accesso da IP sospetto {activity.ip_address} da {user.username}",
                                'details': {
                                    'ip_address': activity.ip_address,
                                    'action': activity.action
                                }
                            }
                            alerts.append(alert)
                            
        except Exception as e:
            logger.error(f"Errore durante controllo IP sospetti: {e}")
        
        return alerts
    
    def _check_blocked_document_attempts(self) -> List[Dict]:
        """
        Identifica tentativi di download su documenti bloccati.
        """
        alerts = []
        
        try:
            # Trova tentativi di download su documenti non scaricabili
            blocked_attempts = DocumentActivityLog.query.filter(
                and_(
                    DocumentActivityLog.action == 'download_denied',
                    DocumentActivityLog.timestamp >= datetime.utcnow() - timedelta(hours=1)
                )
            ).all()
            
            for attempt in blocked_attempts:
                user = User.query.get(attempt.user_id)
                document = Document.query.get(attempt.document_id)
                
                if user and document:
                    alert = {
                        'alert_type': 'tentativo_documento_bloccato',
                        'user_id': attempt.user_id,
                        'document_id': attempt.document_id,
                        'severity': 'media',
                        'description': f"Tentativo di download documento bloccato '{document.title}' da {user.username}",
                        'details': {
                            'document_title': document.title,
                            'reason': attempt.note or 'Documento non scaricabile'
                        }
                    }
                    alerts.append(alert)
                    
        except Exception as e:
            logger.error(f"Errore durante controllo tentativi documenti bloccati: {e}")
        
        return alerts
    
    def create_ai_alert(self, alert_data: Dict) -> Optional[AIAlert]:
        """
        Crea un record AIAlert nel database.
        
        Args:
            alert_data: Dizionario con i dati dell'alert
            
        Returns:
            AIAlert: L'oggetto alert creato
        """
        try:
            # Genera analisi AI del comportamento
            ai_analysis = self._generate_ai_analysis(alert_data)
            
            alert = AIAlert(
                alert_type=alert_data['alert_type'],
                user_id=alert_data['user_id'],
                document_id=alert_data.get('document_id'),
                severity=alert_data['severity'],
                description=alert_data['description'],
                ip_address=alert_data.get('details', {}).get('ip_address'),
                user_agent=alert_data.get('details', {}).get('user_agent'),
                resolved=False
            )
            
            db.session.add(alert)
            db.session.commit()
            
            logger.info(f"Alert AI creato: {alert.id} - {alert.alert_type}")
            return alert
            
        except Exception as e:
            logger.error(f"Errore durante creazione alert AI: {e}")
            db.session.rollback()
            return None
    
    def _generate_ai_analysis(self, alert_data: Dict) -> str:
        """
        Genera analisi AI del comportamento sospetto.
        
        Args:
            alert_data: Dati dell'alert
            
        Returns:
            str: Analisi AI generata
        """
        try:
            prompt = f"""
            Analizza questo pattern di download sospetto:
            
            Tipo Alert: {alert_data['alert_type']}
            Descrizione: {alert_data['description']}
            Severità: {alert_data['severity']}
            Dettagli: {json.dumps(alert_data.get('details', {}), indent=2)}
            
            È sospetto? Quali sono i rischi e cosa consigliare all'admin?
            
            Fornisci:
            1. Valutazione rischio (basso/medio/alto/critico)
            2. Possibili motivazioni legittime
            3. Azioni consigliate per l'admin
            4. Misure preventive
            """
            
            ai_response = get_ai_response(prompt)
            return ai_response or "Analisi AI non disponibile"
            
        except Exception as e:
            logger.error(f"Errore durante generazione analisi AI: {e}")
            return "Errore durante analisi AI"
    
    def send_admin_notification(self, alert: AIAlert) -> bool:
        """
        Invia notifica email all'admin (opzionale).
        
        Args:
            alert: L'alert da notificare
            
        Returns:
            bool: True se inviata con successo
        """
        try:
            # Per ora, logghiamo solo la notifica
            # In futuro, implementare invio email
            logger.info(f"Notifica admin per alert {alert.id}: {alert.description}")
            return True
            
        except Exception as e:
            logger.error(f"Errore durante invio notifica admin: {e}")
            return False
    
    def get_recent_alerts(self, hours: int = 24) -> List[AIAlert]:
        """
        Recupera gli alert recenti.
        
        Args:
            hours: Numero di ore da considerare
            
        Returns:
            List[AIAlert]: Lista degli alert
        """
        try:
            return AIAlert.query.filter(
                AIAlert.created_at >= datetime.utcnow() - timedelta(hours=hours)
            ).order_by(AIAlert.created_at.desc()).all()
            
        except Exception as e:
            logger.error(f"Errore durante recupero alert recenti: {e}")
            return []
    
    def resolve_alert(self, alert_id: int, resolved_by: str) -> bool:
        """
        Marca un alert come risolto.
        
        Args:
            alert_id: ID dell'alert
            resolved_by: Chi ha risolto l'alert
            
        Returns:
            bool: True se risolto con successo
        """
        try:
            alert = AIAlert.query.get(alert_id)
            if alert:
                alert.resolved = True
                alert.resolved_by = resolved_by
                alert.resolved_at = datetime.utcnow()
                db.session.commit()
                return True
            return False
            
        except Exception as e:
            logger.error(f"Errore durante risoluzione alert: {e}")
            db.session.rollback()
            return False
    
    def get_alert_statistics(self) -> Dict:
        """
        Recupera statistiche degli alert.
        
        Returns:
            Dict: Statistiche degli alert
        """
        try:
            total_alerts = AIAlert.query.count()
            resolved_alerts = AIAlert.query.filter(AIAlert.resolved == True).count()
            pending_alerts = total_alerts - resolved_alerts
            
            # Statistiche per severità
            severity_stats = db.session.query(
                AIAlert.severity,
                func.count(AIAlert.id).label('count')
            ).group_by(AIAlert.severity).all()
            
            # Statistiche per tipo
            type_stats = db.session.query(
                AIAlert.alert_type,
                func.count(AIAlert.id).label('count')
            ).group_by(AIAlert.alert_type).all()
            
            return {
                'total': total_alerts,
                'resolved': resolved_alerts,
                'pending': pending_alerts,
                'severity_stats': {s.severity: s.count for s in severity_stats},
                'type_stats': {t.alert_type: t.count for t in type_stats}
            }
            
        except Exception as e:
            logger.error(f"Errore durante recupero statistiche alert: {e}")
            return {}


# Istanza globale del servizio
ai_monitoring_service = AIMonitoringService()


def analizza_download_sospetti() -> List[Dict]:
    """
    Funzione principale per analizzare i download sospetti.
    
    Returns:
        List[Dict]: Lista di alert generati
    """
    return ai_monitoring_service.analizza_download_sospetti()


def create_ai_alert(alert_data: Dict) -> Optional[AIAlert]:
    """
    Crea un alert AI.
    
    Args:
        alert_data: Dati dell'alert
        
    Returns:
        AIAlert: Alert creato
    """
    return ai_monitoring_service.create_ai_alert(alert_data)


def get_recent_alerts(hours: int = 24) -> List[AIAlert]:
    """
    Recupera alert recenti.
    
    Args:
        hours: Ore da considerare
        
    Returns:
        List[AIAlert]: Lista alert
    """
    return ai_monitoring_service.get_recent_alerts(hours)


def get_alert_statistics() -> Dict:
    """
    Recupera statistiche alert.
    
    Returns:
        Dict: Statistiche
    """
    return ai_monitoring_service.get_alert_statistics() 