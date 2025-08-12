"""
Servizio per il detection di pattern anomali nelle richieste di accesso.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy import and_, func, desc
from flask import current_app
from models import db, AccessRequestNew, AccessRequestAlert, AccessRequestAlertSeverity, AccessRequestAlertStatus, User

logger = logging.getLogger(__name__)

class AccessRequestDetector:
    """
    Servizio per rilevare pattern anomali nelle richieste di accesso.
    
    Regole implementate:
    - R1: >3 richieste sullo stesso file dallo stesso utente in 24h
    - R2: >8 richieste da uno stesso utente su file diversi in 24h
    - R3: >5 richieste negate per lo stesso utente in 7gg
    - R4: Richieste da IP nuovi per lo stesso utente con user-agent insolito
    - R5: Spike aziendale: >50 richieste totali in 30min
    """
    
    def __init__(self):
        self.rules = {
            'R1': {'threshold': 3, 'window_hours': 24, 'severity': AccessRequestAlertSeverity.WARNING},
            'R2': {'threshold': 8, 'window_hours': 24, 'severity': AccessRequestAlertSeverity.WARNING},
            'R3': {'threshold': 5, 'window_days': 7, 'severity': AccessRequestAlertSeverity.CRITICAL},
            'R4': {'threshold': 1, 'window_hours': 24, 'severity': AccessRequestAlertSeverity.WARNING},
            'R5': {'threshold': 50, 'window_minutes': 30, 'severity': AccessRequestAlertSeverity.CRITICAL}
        }
    
    def run_access_request_detection(self, now: datetime = None) -> List[AccessRequestAlert]:
        """
        Esegue il detection di pattern anomali nelle richieste di accesso.
        
        Args:
            now (datetime): Timestamp di riferimento (default: datetime.utcnow())
            
        Returns:
            List[AccessRequestAlert]: Lista degli alert generati
        """
        if now is None:
            now = datetime.utcnow()
        
        alerts = []
        
        try:
            # Regola R1: >3 richieste sullo stesso file dallo stesso utente in 24h
            alerts.extend(self._check_rule_r1(now))
            
            # Regola R2: >8 richieste da uno stesso utente su file diversi in 24h
            alerts.extend(self._check_rule_r2(now))
            
            # Regola R3: >5 richieste negate per lo stesso utente in 7gg
            alerts.extend(self._check_rule_r3(now))
            
            # Regola R4: Richieste da IP nuovi per lo stesso utente con user-agent insolito
            alerts.extend(self._check_rule_r4(now))
            
            # Regola R5: Spike aziendale: >50 richieste totali in 30min
            alerts.extend(self._check_rule_r5(now))
            
            # Salva gli alert nel database
            for alert in alerts:
                db.session.add(alert)
            
            db.session.commit()
            
            # Log del detection
            logger.info(f"Access request detection completato: {len(alerts)} alert generati")
            
            # Invia email per alert critici
            critical_alerts = [a for a in alerts if a.severity == AccessRequestAlertSeverity.CRITICAL]
            if critical_alerts:
                self._send_critical_alert_email(critical_alerts)
            
            return alerts
            
        except Exception as e:
            logger.error(f"Errore durante il detection: {str(e)}")
            db.session.rollback()
            return []
    
    def _check_rule_r1(self, now: datetime) -> List[AccessRequestAlert]:
        """
        Regola R1: >3 richieste sullo stesso file dallo stesso utente in 24h.
        """
        alerts = []
        window_start = now - timedelta(hours=24)
        
        # Query per trovare (user_id, file_id) con >3 richieste
        results = db.session.query(
            AccessRequestNew.requested_by,
            AccessRequestNew.file_id,
            func.count(AccessRequestNew.id).label('count')
        ).filter(
            AccessRequestNew.created_at >= window_start
        ).group_by(
            AccessRequestNew.requested_by,
            AccessRequestNew.file_id
        ).having(
            func.count(AccessRequestNew.id) > self.rules['R1']['threshold']
        ).all()
        
        for user_id, file_id, count in results:
            # Verifica se esiste già un alert per questa combinazione
            existing_alert = AccessRequestAlert.query.filter(
                and_(
                    AccessRequestAlert.rule == 'R1',
                    AccessRequestAlert.user_id == user_id,
                    AccessRequestAlert.file_id == file_id,
                    AccessRequestAlert.created_at >= window_start
                )
            ).first()
            
            if not existing_alert:
                # Ottieni dettagli delle richieste
                requests = AccessRequestNew.query.filter(
                    and_(
                        AccessRequestNew.requested_by == user_id,
                        AccessRequestNew.file_id == file_id,
                        AccessRequestNew.created_at >= window_start
                    )
                ).order_by(AccessRequestNew.created_at.desc()).limit(5).all()
                
                details = {
                    'count': count,
                    'threshold': self.rules['R1']['threshold'],
                    'window_hours': 24,
                    'requests': [
                        {
                            'id': req.id,
                            'created_at': req.created_at.isoformat(),
                            'reason': req.reason
                        } for req in requests
                    ]
                }
                
                alert = AccessRequestAlert(
                    rule='R1',
                    severity=self.rules['R1']['severity'],
                    user_id=user_id,
                    file_id=file_id,
                    window_from=window_start,
                    window_to=now,
                    details=json.dumps(details),
                    status=AccessRequestAlertStatus.NEW
                )
                alerts.append(alert)
        
        return alerts
    
    def _check_rule_r2(self, now: datetime) -> List[AccessRequestAlert]:
        """
        Regola R2: >8 richieste da uno stesso utente su file diversi in 24h.
        """
        alerts = []
        window_start = now - timedelta(hours=24)
        
        # Query per trovare user_id con >8 richieste su file distinti
        results = db.session.query(
            AccessRequestNew.requested_by,
            func.count(func.distinct(AccessRequestNew.file_id)).label('distinct_files'),
            func.count(AccessRequestNew.id).label('total_requests')
        ).filter(
            AccessRequestNew.created_at >= window_start
        ).group_by(
            AccessRequestNew.requested_by
        ).having(
            func.count(AccessRequestNew.id) > self.rules['R2']['threshold']
        ).all()
        
        for user_id, distinct_files, total_requests in results:
            # Verifica se esiste già un alert per questo utente
            existing_alert = AccessRequestAlert.query.filter(
                and_(
                    AccessRequestAlert.rule == 'R2',
                    AccessRequestAlert.user_id == user_id,
                    AccessRequestAlert.created_at >= window_start
                )
            ).first()
            
            if not existing_alert:
                # Ottieni dettagli delle richieste
                requests = AccessRequestNew.query.filter(
                    and_(
                        AccessRequestNew.requested_by == user_id,
                        AccessRequestNew.created_at >= window_start
                    )
                ).order_by(AccessRequestNew.created_at.desc()).limit(10).all()
                
                details = {
                    'total_requests': total_requests,
                    'distinct_files': distinct_files,
                    'threshold': self.rules['R2']['threshold'],
                    'window_hours': 24,
                    'requests': [
                        {
                            'id': req.id,
                            'file_id': req.file_id,
                            'created_at': req.created_at.isoformat(),
                            'reason': req.reason
                        } for req in requests
                    ]
                }
                
                alert = AccessRequestAlert(
                    rule='R2',
                    severity=self.rules['R2']['severity'],
                    user_id=user_id,
                    window_from=window_start,
                    window_to=now,
                    details=json.dumps(details),
                    status=AccessRequestAlertStatus.NEW
                )
                alerts.append(alert)
        
        return alerts
    
    def _check_rule_r3(self, now: datetime) -> List[AccessRequestAlert]:
        """
        Regola R3: >5 richieste negate per lo stesso utente in 7gg.
        """
        alerts = []
        window_start = now - timedelta(days=7)
        
        # Query per trovare user_id con >5 richieste negate
        results = db.session.query(
            AccessRequestNew.requested_by,
            func.count(AccessRequestNew.id).label('denied_count')
        ).filter(
            and_(
                AccessRequestNew.created_at >= window_start,
                AccessRequestNew.status == 'denied'
            )
        ).group_by(
            AccessRequestNew.requested_by
        ).having(
            func.count(AccessRequestNew.id) > self.rules['R3']['threshold']
        ).all()
        
        for user_id, denied_count in results:
            # Verifica se esiste già un alert per questo utente
            existing_alert = AccessRequestAlert.query.filter(
                and_(
                    AccessRequestAlert.rule == 'R3',
                    AccessRequestAlert.user_id == user_id,
                    AccessRequestAlert.created_at >= window_start
                )
            ).first()
            
            if not existing_alert:
                # Ottieni dettagli delle richieste negate
                requests = AccessRequestNew.query.filter(
                    and_(
                        AccessRequestNew.requested_by == user_id,
                        AccessRequestNew.status == 'denied',
                        AccessRequestNew.created_at >= window_start
                    )
                ).order_by(AccessRequestNew.created_at.desc()).limit(10).all()
                
                details = {
                    'denied_count': denied_count,
                    'threshold': self.rules['R3']['threshold'],
                    'window_days': 7,
                    'requests': [
                        {
                            'id': req.id,
                            'file_id': req.file_id,
                            'created_at': req.created_at.isoformat(),
                            'reason': req.reason,
                            'decision_reason': req.decision_reason
                        } for req in requests
                    ]
                }
                
                alert = AccessRequestAlert(
                    rule='R3',
                    severity=self.rules['R3']['severity'],
                    user_id=user_id,
                    window_from=window_start,
                    window_to=now,
                    details=json.dumps(details),
                    status=AccessRequestAlertStatus.NEW
                )
                alerts.append(alert)
                
                # Applica cooldown per 24 ore
                self._apply_user_cooldown(user_id, now + timedelta(hours=24))
        
        return alerts
    
    def _check_rule_r4(self, now: datetime) -> List[AccessRequestAlert]:
        """
        Regola R4: Richieste da IP nuovi per lo stesso utente con user-agent insolito.
        """
        alerts = []
        window_start = now - timedelta(hours=24)
        
        # Per ora implementiamo una versione semplificata
        # In futuro si può migliorare con analisi più sofisticata degli IP/UA
        
        # Query per trovare utenti con richieste da IP diversi
        results = db.session.query(
            AccessRequestNew.requested_by,
            func.count(func.distinct(AccessRequestNew.ip_address)).label('distinct_ips')
        ).filter(
            and_(
                AccessRequestNew.created_at >= window_start,
                AccessRequestNew.ip_address.isnot(None)
            )
        ).group_by(
            AccessRequestNew.requested_by
        ).having(
            func.count(func.distinct(AccessRequestNew.ip_address)) > 2
        ).all()
        
        for user_id, distinct_ips in results:
            # Verifica se esiste già un alert per questo utente
            existing_alert = AccessRequestAlert.query.filter(
                and_(
                    AccessRequestAlert.rule == 'R4',
                    AccessRequestAlert.user_id == user_id,
                    AccessRequestAlert.created_at >= window_start
                )
            ).first()
            
            if not existing_alert:
                # Ottieni dettagli delle richieste
                requests = AccessRequestNew.query.filter(
                    and_(
                        AccessRequestNew.requested_by == user_id,
                        AccessRequestNew.created_at >= window_start
                    )
                ).order_by(AccessRequestNew.created_at.desc()).limit(5).all()
                
                details = {
                    'distinct_ips': distinct_ips,
                    'window_hours': 24,
                    'requests': [
                        {
                            'id': req.id,
                            'ip_address': req.ip_address,
                            'user_agent': req.user_agent,
                            'created_at': req.created_at.isoformat()
                        } for req in requests
                    ]
                }
                
                alert = AccessRequestAlert(
                    rule='R4',
                    severity=self.rules['R4']['severity'],
                    user_id=user_id,
                    window_from=window_start,
                    window_to=now,
                    details=json.dumps(details),
                    status=AccessRequestAlertStatus.NEW
                )
                alerts.append(alert)
        
        return alerts
    
    def _check_rule_r5(self, now: datetime) -> List[AccessRequestAlert]:
        """
        Regola R5: Spike aziendale: >50 richieste totali in 30min.
        """
        alerts = []
        window_start = now - timedelta(minutes=30)
        
        # Conta richieste totali nell'ultima mezz'ora
        total_requests = AccessRequestNew.query.filter(
            AccessRequestNew.created_at >= window_start
        ).count()
        
        if total_requests > self.rules['R5']['threshold']:
            # Verifica se esiste già un alert per questo periodo
            existing_alert = AccessRequestAlert.query.filter(
                and_(
                    AccessRequestAlert.rule == 'R5',
                    AccessRequestAlert.created_at >= window_start
                )
            ).first()
            
            if not existing_alert:
                # Ottieni dettagli delle richieste
                requests = AccessRequestNew.query.filter(
                    AccessRequestNew.created_at >= window_start
                ).order_by(AccessRequestNew.created_at.desc()).limit(20).all()
                
                details = {
                    'total_requests': total_requests,
                    'threshold': self.rules['R5']['threshold'],
                    'window_minutes': 30,
                    'requests': [
                        {
                            'id': req.id,
                            'user_id': req.requested_by,
                            'file_id': req.file_id,
                            'created_at': req.created_at.isoformat()
                        } for req in requests
                    ]
                }
                
                alert = AccessRequestAlert(
                    rule='R5',
                    severity=self.rules['R5']['severity'],
                    window_from=window_start,
                    window_to=now,
                    details=json.dumps(details),
                    status=AccessRequestAlertStatus.NEW
                )
                alerts.append(alert)
        
        return alerts
    
    def _apply_user_cooldown(self, user_id: int, cooldown_until: datetime):
        """
        Applica un cooldown temporaneo a un utente.
        """
        try:
            user = User.query.get(user_id)
            if user:
                user.cooldown_until = cooldown_until
                db.session.commit()
                logger.info(f"Cooldown applicato all'utente {user_id} fino a {cooldown_until}")
        except Exception as e:
            logger.error(f"Errore nell'applicazione del cooldown: {str(e)}")
    
    def _send_critical_alert_email(self, critical_alerts: List[AccessRequestAlert]):
        """
        Invia email per alert critici.
        """
        try:
            from flask import render_template
            from extensions import mail
            from flask_mail import Message
            from models import User
            
            # Ottieni tutti gli admin attivi
            admins = User.query.filter_by(is_admin=True, is_active=True).all()
            admin_emails = [admin.email for admin in admins if admin.email]
            
            if not admin_emails:
                logger.warning("Nessun admin trovato per invio email alert critici")
                return
            
            for alert in critical_alerts:
                try:
                    # Prepara i dettagli per il template
                    details = alert.details_json
                    
                    # Crea il messaggio email
                    subject = f"🚨 Alert Critico Richieste Accesso - {alert.rule}"
                    msg = Message(
                        subject=subject,
                        recipients=admin_emails,
                        html=render_template(
                            'email/access_alert_critical.html',
                            alert=alert,
                            details=details
                        )
                    )
                    
                    # Invia email
                    mail.send(msg)
                    logger.info(f"Email alert critico inviata per {alert.rule} - User: {alert.user_id}")
                    
                except Exception as e:
                    logger.error(f"Errore nell'invio email per alert {alert.id}: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Errore nell'invio email alert critici: {str(e)}")
    
    def check_user_cooldown(self, user_id: int) -> bool:
        """
        Verifica se un utente è in cooldown.
        
        Args:
            user_id (int): ID dell'utente
            
        Returns:
            bool: True se l'utente è in cooldown
        """
        try:
            user = User.query.get(user_id)
            if user and user.cooldown_until:
                if datetime.utcnow() < user.cooldown_until:
                    return True
                else:
                    # Rimuovi il cooldown scaduto
                    user.cooldown_until = None
                    db.session.commit()
            return False
        except Exception as e:
            logger.error(f"Errore nel controllo cooldown: {str(e)}")
            return False

# Istanza globale del detector
access_request_detector = AccessRequestDetector()
