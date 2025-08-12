"""
Servizio AI per il rilevamento di download sospetti.
Analizza i log di download in tempo reale e genera alert.
"""

import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from sqlalchemy import func, and_
from flask import current_app
from models import DownloadLog, DownloadAlert, User, db, DownloadAlertStatus


class DownloadAlertDetector:
    """
    Servizio per il rilevamento di download sospetti tramite AI.
    """
    
    def __init__(self):
        """Inizializza il detector con le regole di base."""
        self.rules = {
            'massive_download': {
                'enabled': True,
                'threshold': 10,  # download in 5 minuti
                'time_window': 5,  # minuti
                'severity': 'high'
            },
            'suspicious_time': {
                'enabled': True,
                'start_hour': 6,  # prima delle 6:00
                'end_hour': 23,   # dopo le 23:00
                'severity': 'medium'
            },
            'ip_change': {
                'enabled': True,
                'severity': 'medium'
            },
            'unusual_user_activity': {
                'enabled': True,
                'threshold': 20,  # download in 1 ora
                'time_window': 60,  # minuti
                'severity': 'high'
            }
        }
    
    def check_suspicious_download(self, user_id: int, document_id: int, 
                                filename: str, ip_address: str, 
                                timestamp: datetime) -> List[Dict]:
        """
        Controlla se un download è sospetto applicando tutte le regole.
        
        Args:
            user_id: ID dell'utente
            document_id: ID del documento
            filename: Nome del file
            ip_address: Indirizzo IP
            timestamp: Data/ora del download
            
        Returns:
            Lista di alert generati
        """
        alerts = []
        
        # Regola 1: Download massivo
        if self.rules['massive_download']['enabled']:
            massive_alert = self._check_massive_download(user_id, timestamp)
            if massive_alert:
                alerts.append(massive_alert)
        
        # Regola 2: Orario sospetto
        if self.rules['suspicious_time']['enabled']:
            time_alert = self._check_suspicious_time(timestamp)
            if time_alert:
                alerts.append(time_alert)
        
        # Regola 3: Cambio IP
        if self.rules['ip_change']['enabled']:
            ip_alert = self._check_ip_change(user_id, ip_address, timestamp)
            if ip_alert:
                alerts.append(ip_alert)
        
        # Regola 4: Attività insolita dell'utente
        if self.rules['unusual_user_activity']['enabled']:
            activity_alert = self._check_unusual_activity(user_id, timestamp)
            if activity_alert:
                alerts.append(activity_alert)
        
        return alerts
    
    def _check_massive_download(self, user_id: int, timestamp: datetime) -> Optional[Dict]:
        """
        Controlla se l'utente ha fatto troppi download in poco tempo.
        
        Args:
            user_id: ID dell'utente
            timestamp: Data/ora del download
            
        Returns:
            Alert se rilevato, None altrimenti
        """
        rule = self.rules['massive_download']
        time_window = timestamp - timedelta(minutes=rule['time_window'])
        
        # Conta download recenti dell'utente
        recent_downloads = DownloadLog.query.filter(
            and_(
                DownloadLog.user_id == user_id,
                DownloadLog.timestamp >= time_window,
                DownloadLog.timestamp <= timestamp
            )
        ).count()
        
        if recent_downloads >= rule['threshold']:
            return {
                'reason': 'download_massivo',
                'severity': rule['severity'],
                'details': json.dumps({
                    'download_count': recent_downloads,
                    'time_window_minutes': rule['time_window'],
                    'threshold': rule['threshold']
                })
            }
        
        return None
    
    def _check_suspicious_time(self, timestamp: datetime) -> Optional[Dict]:
        """
        Controlla se il download è avvenuto in orario sospetto.
        
        Args:
            timestamp: Data/ora del download
            
        Returns:
            Alert se rilevato, None altrimenti
        """
        rule = self.rules['suspicious_time']
        hour = timestamp.hour
        
        if hour < rule['start_hour'] or hour >= rule['end_hour']:
            return {
                'reason': 'orario_sospetto',
                'severity': rule['severity'],
                'details': json.dumps({
                    'hour': hour,
                    'start_hour': rule['start_hour'],
                    'end_hour': rule['end_hour']
                })
            }
        
        return None
    
    def _check_ip_change(self, user_id: int, ip_address: str, 
                        timestamp: datetime) -> Optional[Dict]:
        """
        Controlla se l'IP è diverso dall'ultimo IP conosciuto dell'utente.
        
        Args:
            user_id: ID dell'utente
            ip_address: IP corrente
            timestamp: Data/ora del download
            
        Returns:
            Alert se rilevato, None altrimenti
        """
        rule = self.rules['ip_change']
        
        # Trova l'ultimo download dell'utente
        last_download = DownloadLog.query.filter(
            DownloadLog.user_id == user_id
        ).order_by(DownloadLog.timestamp.desc()).first()
        
        if last_download and last_download.ip_address != ip_address:
            return {
                'reason': 'ip_sospetto',
                'severity': rule['severity'],
                'details': json.dumps({
                    'current_ip': ip_address,
                    'previous_ip': last_download.ip_address,
                    'time_since_last': (timestamp - last_download.timestamp).total_seconds() / 3600
                })
            }
        
        return None
    
    def _check_unusual_activity(self, user_id: int, timestamp: datetime) -> Optional[Dict]:
        """
        Controlla se l'utente ha un'attività insolita (troppi download in un'ora).
        
        Args:
            user_id: ID dell'utente
            timestamp: Data/ora del download
            
        Returns:
            Alert se rilevato, None altrimenti
        """
        rule = self.rules['unusual_user_activity']
        time_window = timestamp - timedelta(minutes=rule['time_window'])
        
        # Conta download dell'utente nell'ultima ora
        hourly_downloads = DownloadLog.query.filter(
            and_(
                DownloadLog.user_id == user_id,
                DownloadLog.timestamp >= time_window,
                DownloadLog.timestamp <= timestamp
            )
        ).count()
        
        if hourly_downloads >= rule['threshold']:
            return {
                'reason': 'attivita_insolita',
                'severity': rule['severity'],
                'details': json.dumps({
                    'download_count': hourly_downloads,
                    'time_window_minutes': rule['time_window'],
                    'threshold': rule['threshold']
                })
            }
        
        return None
    
    def create_alert(self, user_id: int, document_id: int, filename: str,
                    ip_address: str, timestamp: datetime, alert_data: Dict) -> DownloadAlert:
        """
        Crea un nuovo alert nel database.
        
        Args:
            user_id: ID dell'utente
            document_id: ID del documento
            filename: Nome del file
            ip_address: Indirizzo IP
            timestamp: Data/ora del download
            alert_data: Dati dell'alert
            
        Returns:
            Oggetto DownloadAlert creato
        """
        alert = DownloadAlert(
            user_id=user_id,
            document_id=document_id,
            filename=filename,
            reason=alert_data['reason'],
            ip_address=ip_address,
            timestamp=timestamp,
            severity=alert_data['severity'],
            details=alert_data.get('details'),
            status=DownloadAlertStatus.NEW
        )
        
        db.session.add(alert)
        db.session.commit()
        
        current_app.logger.info(f"Alert creato: {alert}")
        return alert
    
    def get_alerts_summary(self) -> Dict:
        """
        Ottiene un riepilogo degli alert per la dashboard.
        
        Returns:
            Dizionario con statistiche degli alert
        """
        total_alerts = DownloadAlert.query.count()
        new_alerts = DownloadAlert.query.filter_by(status=DownloadAlertStatus.NEW).count()
        seen_alerts = DownloadAlert.query.filter_by(status=DownloadAlertStatus.SEEN).count()
        resolved_alerts = DownloadAlert.query.filter_by(status=DownloadAlertStatus.RESOLVED).count()
        
        # Alert per gravità
        high_severity = DownloadAlert.query.filter_by(severity='high').count()
        medium_severity = DownloadAlert.query.filter_by(severity='medium').count()
        low_severity = DownloadAlert.query.filter_by(severity='low').count()
        
        # Alert per motivo
        reasons = db.session.query(
            DownloadAlert.reason,
            func.count(DownloadAlert.id).label('count')
        ).group_by(DownloadAlert.reason).all()
        
        return {
            'total': total_alerts,
            'new': new_alerts,
            'seen': seen_alerts,
            'resolved': resolved_alerts,
            'severity': {
                'high': high_severity,
                'medium': medium_severity,
                'low': low_severity
            },
            'reasons': {reason: count for reason, count in reasons}
        }


# Istanza globale del detector
alert_detector = DownloadAlertDetector()
