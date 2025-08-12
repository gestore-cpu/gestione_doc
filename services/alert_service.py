"""
Servizio per rilevamento e gestione di alert di sicurezza.
Implementa regole per identificare comportamenti anomali degli utenti.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from collections import defaultdict

from flask import current_app, request
from extensions import db
from models import SecurityAlert, SecurityAuditLog, User, Document, SeverityLevel, AlertStatus

logger = logging.getLogger(__name__)


class AlertService:
    """
    Servizio per rilevamento e gestione alert di sicurezza.
    """
    
    def __init__(self):
        """Inizializza il servizio alert."""
        # Configurazione da variabili ambiente
        self.burst_threshold = int(os.getenv('ALERT_BURST_THRESHOLD', '10'))
        self.burst_window_minutes = int(os.getenv('ALERT_BURST_WINDOW_MIN', '5'))
        self.enabled = True
    
    def get_client_ip(self) -> str:
        """Ottiene l'IP del client dal request."""
        try:
            if request.environ.get('HTTP_X_FORWARDED_FOR'):
                return request.environ['HTTP_X_FORWARDED_FOR'].split(',')[0].strip()
            elif request.environ.get('HTTP_X_REAL_IP'):
                return request.environ['HTTP_X_REAL_IP']
            else:
                return request.environ.get('REMOTE_ADDR', 'unknown')
        except:
            return 'unknown'
    
    def create_alert(self, user_id: int, rule_id: str, severity: SeverityLevel, 
                    details: str, metadata: Dict = None) -> Optional[SecurityAlert]:
        """
        Crea un nuovo alert di sicurezza.
        
        Args:
            user_id: ID dell'utente coinvolto
            rule_id: ID della regola che ha generato l'alert
            severity: Livello di severità
            details: Descrizione dell'alert
            metadata: Metadati aggiuntivi
            
        Returns:
            SecurityAlert creato o None se errore
        """
        try:
            # Evita duplicati recenti (stessa regola, stesso utente negli ultimi 10 minuti)
            recent_cutoff = datetime.utcnow() - timedelta(minutes=10)
            existing_alert = SecurityAlert.query.filter(
                SecurityAlert.user_id == user_id,
                SecurityAlert.rule_id == rule_id,
                SecurityAlert.ts >= recent_cutoff,
                SecurityAlert.status == AlertStatus.OPEN
            ).first()
            
            if existing_alert:
                logger.info(f"Alert duplicato evitato per regola {rule_id} utente {user_id}")
                return existing_alert
            
            # Crea nuovo alert
            alert = SecurityAlert(
                user_id=user_id,
                rule_id=rule_id,
                severity=severity,
                details=details,
                status=AlertStatus.OPEN
            )
            
            db.session.add(alert)
            db.session.commit()
            
            logger.warning(f"Alert creato: {rule_id} per utente {user_id} - {severity.value}")
            
            # Invia notifica email se severità alta
            if severity in [SeverityLevel.HIGH]:
                self.send_admin_notification(alert, metadata)
            
            return alert
            
        except Exception as e:
            logger.error(f"Errore creazione alert: {e}")
            db.session.rollback()
            return None
    
    def send_admin_notification(self, alert: SecurityAlert, metadata: Dict = None):
        """
        Invia notifica email agli amministratori per alert critici.
        
        Args:
            alert: Alert di sicurezza
            metadata: Metadati aggiuntivi
        """
        try:
            from flask_mail import Message
            from app import mail
            
            # Trova email amministratori
            admins = User.query.filter(User.role.in_(['admin', 'superadmin'])).all()
            admin_emails = [admin.email for admin in admins]
            
            if not admin_emails:
                logger.warning("Nessun amministratore trovato per notifica alert")
                return
            
            # Prepara messaggio
            subject = f"🚨 Security Alert - {alert.rule_id} (Severity: {alert.severity.value.upper()})"
            
            body = f"""
🚨 SECURITY ALERT DETECTED

📋 Alert Details:
- Rule ID: {alert.rule_id}
- Severity: {alert.severity.value.upper()}
- User: {alert.user.username} ({alert.user.email})
- Timestamp: {alert.ts.strftime('%d/%m/%Y %H:%M:%S')}
- Status: {alert.status.value}

📄 Description:
{alert.details}

🔗 Admin Panel: {current_app.config.get('BASE_URL', '')}/admin/alerts/{alert.id}

---
Document Management System
Security Monitoring
            """.strip()
            
            # Invia email
            msg = Message(
                subject=subject,
                recipients=admin_emails,
                body=body,
                sender=current_app.config.get('MAIL_DEFAULT_SENDER', 'security@mercurysurgelati.org')
            )
            
            mail.send(msg)
            logger.info(f"Notifica alert inviata a {len(admin_emails)} amministratori")
            
        except Exception as e:
            logger.error(f"Errore invio notifica alert: {e}")
    
    def check_burst_downloads(self, user_id: int, action: str, object_id: int) -> bool:
        """
        Regola 1: Controlla download eccessivi in un breve periodo.
        
        Args:
            user_id: ID utente
            action: Azione eseguita
            object_id: ID oggetto
            
        Returns:
            bool: True se alert generato
        """
        if action not in ['file_download_success', 'file_view_success']:
            return False
        
        try:
            # Periodo di controllo
            window_start = datetime.utcnow() - timedelta(minutes=self.burst_window_minutes)
            
            # Conta download recenti
            recent_downloads = SecurityAuditLog.query.filter(
                SecurityAuditLog.user_id == user_id,
                SecurityAuditLog.action.in_(['file_download_success', 'file_view_success']),
                SecurityAuditLog.ts >= window_start
            ).count()
            
            if recent_downloads >= self.burst_threshold:
                # Genera alert
                details = f"Utente ha effettuato {recent_downloads} download/visualizzazioni negli ultimi {self.burst_window_minutes} minuti (soglia: {self.burst_threshold})"
                
                self.create_alert(
                    user_id=user_id,
                    rule_id='burst_downloads',
                    severity=SeverityLevel.MEDIUM,
                    details=details,
                    metadata={'download_count': recent_downloads, 'window_minutes': self.burst_window_minutes}
                )
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Errore controllo burst downloads: {e}")
            return False
    
    def check_new_ip_access(self, user_id: int, action: str, object_id: int) -> bool:
        """
        Regola 2: Controlla accesso da IP nuovo per l'utente.
        
        Args:
            user_id: ID utente
            action: Azione eseguita
            object_id: ID oggetto
            
        Returns:
            bool: True se alert generato
        """
        if action not in ['file_download_success', 'file_view_success', 'auth_login_success']:
            return False
        
        try:
            current_ip = self.get_client_ip()
            
            if current_ip == 'unknown':
                return False
            
            # Cerca IP precedenti per questo utente (ultimi 90 giorni)
            since_date = datetime.utcnow() - timedelta(days=90)
            
            previous_ips = db.session.query(SecurityAuditLog.ip)\
                                   .filter(SecurityAuditLog.user_id == user_id,
                                          SecurityAuditLog.ts >= since_date)\
                                   .distinct().all()
            
            previous_ip_list = [ip[0] for ip in previous_ips]
            
            if current_ip not in previous_ip_list:
                # IP nuovo rilevato
                details = f"Accesso da nuovo IP {current_ip}. IP precedenti: {', '.join(previous_ip_list[-5:])}"
                
                self.create_alert(
                    user_id=user_id,
                    rule_id='new_ip_access',
                    severity=SeverityLevel.LOW,
                    details=details,
                    metadata={'new_ip': current_ip, 'previous_ips': previous_ip_list[-10:]}
                )
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Errore controllo nuovo IP: {e}")
            return False
    
    def check_cross_department_access(self, user_id: int, action: str, object_id: int) -> bool:
        """
        Regola 3: Controlla accesso a file di reparto diverso dall'utente.
        
        Args:
            user_id: ID utente
            action: Azione eseguita
            object_id: ID del documento
            
        Returns:
            bool: True se alert generato
        """
        if action not in ['file_download_success', 'file_view_success'] or not object_id:
            return False
        
        try:
            # Ottieni utente e documento
            user = User.query.get(user_id)
            document = Document.query.get(object_id)
            
            if not user or not document:
                return False
            
            # Ottieni reparti dell'utente
            user_departments = [dept.id for dept in user.departments] if user.departments else []
            
            # Se l'utente è admin, non applicare la regola
            if user.role in ['admin', 'superadmin']:
                return False
            
            # Se il documento appartiene a un reparto diverso
            if document.department_id and document.department_id not in user_departments:
                # Controlla se l'accesso è autorizzato (es. documento pubblico)
                if document.visibility == 'pubblico':
                    return False
                
                # Genera alert
                user_dept_names = [dept.name for dept in user.departments] if user.departments else ['Nessuno']
                doc_dept_name = document.department.name if document.department else 'Sconosciuto'
                
                details = f"Accesso a documento del reparto '{doc_dept_name}' da utente del reparto '{', '.join(user_dept_names)}'"
                
                self.create_alert(
                    user_id=user_id,
                    rule_id='cross_department_access',
                    severity=SeverityLevel.HIGH,
                    details=details,
                    metadata={
                        'document_id': document.id,
                        'document_title': document.title,
                        'document_department': doc_dept_name,
                        'user_departments': user_dept_names
                    }
                )
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Errore controllo accesso cross-reparto: {e}")
            return False
    
    def check_alert_rules(self, user_id: int, action: str, object_id: int = None) -> List[str]:
        """
        Controlla tutte le regole di alert per un'azione.
        
        Args:
            user_id: ID utente
            action: Azione eseguita
            object_id: ID oggetto (opzionale)
            
        Returns:
            List[str]: Lista degli alert generati (rule_id)
        """
        if not self.enabled:
            return []
        
        triggered_alerts = []
        
        try:
            # Regola 1: Burst downloads
            if self.check_burst_downloads(user_id, action, object_id):
                triggered_alerts.append('burst_downloads')
            
            # Regola 2: Nuovo IP
            if self.check_new_ip_access(user_id, action, object_id):
                triggered_alerts.append('new_ip_access')
            
            # Regola 3: Accesso cross-reparto
            if self.check_cross_department_access(user_id, action, object_id):
                triggered_alerts.append('cross_department_access')
            
            if triggered_alerts:
                logger.info(f"Alert generati per utente {user_id}: {triggered_alerts}")
            
            return triggered_alerts
            
        except Exception as e:
            logger.error(f"Errore controllo regole alert: {e}")
            return []
    
    def get_open_alerts(self, limit: int = 50, severity_filter: str = None, 
                       user_id_filter: int = None) -> List[SecurityAlert]:
        """
        Ottiene gli alert aperti.
        
        Args:
            limit: Numero massimo di risultati
            severity_filter: Filtra per severità
            user_id_filter: Filtra per utente
            
        Returns:
            List[SecurityAlert]: Lista alert aperti
        """
        try:
            query = SecurityAlert.query.filter(SecurityAlert.status == AlertStatus.OPEN)
            
            if severity_filter:
                query = query.filter(SecurityAlert.severity == SeverityLevel(severity_filter))
            
            if user_id_filter:
                query = query.filter(SecurityAlert.user_id == user_id_filter)
            
            return query.order_by(SecurityAlert.ts.desc()).limit(limit).all()
            
        except Exception as e:
            logger.error(f"Errore recupero alert aperti: {e}")
            return []
    
    def close_alert(self, alert_id: int, closed_by_user_id: int, note: str = None) -> bool:
        """
        Chiude un alert.
        
        Args:
            alert_id: ID dell'alert
            closed_by_user_id: ID utente che chiude l'alert
            note: Nota di chiusura
            
        Returns:
            bool: True se chiuso con successo
        """
        try:
            alert = SecurityAlert.query.get(alert_id)
            if not alert:
                return False
            
            alert.status = AlertStatus.CLOSED
            db.session.commit()
            
            # Log dell'evento
            from utils.audit_utils import log_audit_event
            log_audit_event(
                closed_by_user_id,
                'alert_closed',
                'security_alert',
                alert_id,
                {'note': note, 'rule_id': alert.rule_id}
            )
            
            logger.info(f"Alert {alert_id} chiuso da utente {closed_by_user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Errore chiusura alert {alert_id}: {e}")
            db.session.rollback()
            return False
    
    def get_alert_statistics(self, days: int = 30) -> Dict[str, Any]:
        """
        Ottiene statistiche degli alert.
        
        Args:
            days: Numero di giorni da considerare
            
        Returns:
            Dict: Statistiche alert
        """
        try:
            since_date = datetime.utcnow() - timedelta(days=days)
            
            # Contatori base
            total_alerts = SecurityAlert.query.filter(SecurityAlert.ts >= since_date).count()
            open_alerts = SecurityAlert.query.filter(
                SecurityAlert.ts >= since_date,
                SecurityAlert.status == AlertStatus.OPEN
            ).count()
            
            # Contatori per severità
            severity_counts = {}
            for severity in SeverityLevel:
                count = SecurityAlert.query.filter(
                    SecurityAlert.ts >= since_date,
                    SecurityAlert.severity == severity
                ).count()
                severity_counts[severity.value] = count
            
            # Contatori per regola
            rule_counts = {}
            rules_query = db.session.query(
                SecurityAlert.rule_id,
                db.func.count(SecurityAlert.id).label('count')
            ).filter(SecurityAlert.ts >= since_date)\
             .group_by(SecurityAlert.rule_id).all()
            
            for rule_id, count in rules_query:
                rule_counts[rule_id] = count
            
            return {
                'period_days': days,
                'total_alerts': total_alerts,
                'open_alerts': open_alerts,
                'closed_alerts': total_alerts - open_alerts,
                'severity_breakdown': severity_counts,
                'rule_breakdown': rule_counts,
                'most_triggered_rule': max(rule_counts.items(), key=lambda x: x[1])[0] if rule_counts else None
            }
            
        except Exception as e:
            logger.error(f"Errore statistiche alert: {e}")
            return {
                'period_days': days,
                'total_alerts': 0,
                'open_alerts': 0,
                'closed_alerts': 0,
                'severity_breakdown': {},
                'rule_breakdown': {},
                'most_triggered_rule': None,
                'error': str(e)
            }


# Istanza globale del servizio
alert_service = AlertService()
