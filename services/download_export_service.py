"""
Servizio per l'export CSV dei log download con streaming e filtri.
Gestisce filtri, rate limiting e streaming per grandi dataset.
"""

import csv
import io
from datetime import datetime, timedelta
from typing import Generator, Dict, Any, Optional
from sqlalchemy import and_, or_, func
from flask import current_app, request
from models import DownloadLog, User, Document, db
from functools import wraps
import time


class DownloadExportService:
    """
    Servizio per l'export CSV dei log download.
    """
    
    def __init__(self):
        """Inizializza il servizio."""
        self.rate_limit_window = 60  # secondi
        self.rate_limit_max = 10     # export per finestra
        self.export_logs = {}        # Cache per rate limiting
    
    def validate_filters(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida e normalizza i filtri di input.
        
        Args:
            filters: Dizionario con i filtri
            
        Returns:
            Dizionario con filtri validati
        """
        validated = {}
        
        # Date filters
        if filters.get('from'):
            try:
                validated['from'] = datetime.strptime(filters['from'], '%Y-%m-%d')
            except ValueError:
                validated['from'] = datetime.now() - timedelta(days=30)
        else:
            validated['from'] = datetime.now() - timedelta(days=30)
        
        if filters.get('to'):
            try:
                to_date = datetime.strptime(filters['to'], '%Y-%m-%d')
                # Include tutto il giorno (fino a 23:59:59)
                validated['to'] = to_date.replace(hour=23, minute=59, second=59)
            except ValueError:
                validated['to'] = datetime.now()
        else:
            validated['to'] = datetime.now()
        
        # User filters
        if filters.get('user_id'):
            try:
                validated['user_id'] = int(filters['user_id'])
            except (ValueError, TypeError):
                validated['user_id'] = None
        
        if filters.get('username'):
            validated['username'] = filters['username'].strip()
        
        # Document filters
        if filters.get('filename'):
            validated['filename'] = filters['filename'].strip()
        
        # IP filter
        if filters.get('ip'):
            validated['ip'] = filters['ip'].strip()
        
        # Status filter
        if filters.get('status') in ['success', 'blocked']:
            validated['status'] = filters['status']
        
        # Source filter
        if filters.get('source') in ['web', 'api']:
            validated['source'] = filters['source']
        
        return validated
    
    def build_query(self, filters: Dict[str, Any]):
        """
        Costruisce la query con i filtri applicati.
        
        Args:
            filters: Dizionario con i filtri validati
            
        Returns:
            Query SQLAlchemy filtrata
        """
        query = DownloadLog.query.join(User).join(Document)
        
        # Filtro date
        if filters.get('from'):
            query = query.filter(DownloadLog.timestamp >= filters['from'])
        if filters.get('to'):
            query = query.filter(DownloadLog.timestamp <= filters['to'])
        
        # Filtro user_id
        if filters.get('user_id'):
            query = query.filter(DownloadLog.user_id == filters['user_id'])
        
        # Filtro username (ricerca parziale)
        if filters.get('username'):
            query = query.filter(User.username.ilike(f"%{filters['username']}%"))
        
        # Filtro filename (ricerca parziale)
        if filters.get('filename'):
            query = query.filter(Document.filename.ilike(f"%{filters['filename']}%"))
        
        # Filtro IP
        if filters.get('ip'):
            query = query.filter(DownloadLog.ip_address.ilike(f"%{filters['ip']}%"))
        
        # Filtro status
        if filters.get('status'):
            query = query.filter(DownloadLog.status == filters['status'])
        
        # Filtro source
        if filters.get('source'):
            query = query.filter(DownloadLog.source == filters['source'])
        
        return query.order_by(DownloadLog.timestamp.desc())
    
    def get_csv_header(self) -> str:
        """
        Restituisce l'header del CSV.
        
        Returns:
            Stringa con header CSV
        """
        return "timestamp,user_id,username,filename,filesize,ip,user_agent,status,reason_block,source\n"
    
    def format_csv_row(self, log: DownloadLog) -> str:
        """
        Formatta una riga del CSV.
        
        Args:
            log: Oggetto DownloadLog
            
        Returns:
            Stringa con riga CSV
        """
        # Escape delle virgole e delle virgolette nei campi
        def escape_field(field):
            if field is None:
                return ""
            field_str = str(field)
            if ',' in field_str or '"' in field_str or '\n' in field_str:
                return f'"{field_str.replace('"', '""')}"'
            return field_str
        
        fields = [
            log.timestamp.strftime('%Y-%m-%d %H:%M:%S') if log.timestamp else '',
            str(log.user_id) if log.user_id else '',
            escape_field(log.username),
            escape_field(log.filename),
            str(log.filesize) if log.filesize else '',
            escape_field(log.ip_address),
            escape_field(log.user_agent),
            escape_field(log.status),
            escape_field(log.reason_block),
            escape_field(log.source)
        ]
        
        return ','.join(fields) + '\n'
    
    def generate_csv_stream(self, filters: Dict[str, Any], chunk_size: int = 1000) -> Generator[str, None, None]:
        """
        Genera lo stream CSV con i dati filtrati.
        
        Args:
            filters: Dizionario con i filtri
            chunk_size: Dimensione del chunk per lo streaming
            
        Yields:
            Chunk di dati CSV
        """
        # Validazione filtri
        validated_filters = self.validate_filters(filters)
        
        # Costruzione query
        query = self.build_query(validated_filters)
        
        # Yield header
        yield self.get_csv_header()
        
        # Streaming dei dati
        offset = 0
        while True:
            chunk = query.offset(offset).limit(chunk_size).all()
            
            if not chunk:
                break
            
            # Formatta e yield il chunk
            chunk_data = ''.join(self.format_csv_row(log) for log in chunk)
            yield chunk_data
            
            offset += chunk_size
            
            # Log progresso per dataset grandi
            if offset % 10000 == 0:
                current_app.logger.info(f"Export progress: {offset} records processed")
    
    def check_rate_limit(self, admin_id: int) -> bool:
        """
        Controlla il rate limit per l'export.
        
        Args:
            admin_id: ID dell'admin
            
        Returns:
            True se l'export è permesso, False altrimenti
        """
        now = time.time()
        admin_key = f"admin_{admin_id}"
        
        # Pulisci export vecchi
        if admin_key in self.export_logs:
            self.export_logs[admin_key] = [
                ts for ts in self.export_logs[admin_key] 
                if now - ts < self.rate_limit_window
            ]
        else:
            self.export_logs[admin_key] = []
        
        # Controlla se supera il limite
        if len(self.export_logs[admin_key]) >= self.rate_limit_max:
            return False
        
        # Aggiungi timestamp corrente
        self.export_logs[admin_key].append(now)
        return True
    
    def log_export(self, admin_id: int, filters: Dict[str, Any], record_count: int):
        """
        Logga l'evento di export.
        
        Args:
            admin_id: ID dell'admin
            filters: Filtri applicati
            record_count: Numero di record esportati
        """
        try:
            from models import AdminLog
            log = AdminLog(
                action='export_download_logs',
                performed_by=f"admin_{admin_id}",
                extra_info=f"Filters: {filters}, Records: {record_count}"
            )
            db.session.add(log)
            db.session.commit()
            
            current_app.logger.info(
                f"Export logged: admin={admin_id}, filters={filters}, count={record_count}"
            )
        except Exception as e:
            current_app.logger.error(f"Error logging export: {e}")
    
    def get_export_stats(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ottiene statistiche per l'export.
        
        Args:
            filters: Dizionario con i filtri
            
        Returns:
            Dizionario con statistiche
        """
        validated_filters = self.validate_filters(filters)
        query = self.build_query(validated_filters)
        
        # Conteggio totale
        total_count = query.count()
        
        # Statistiche per status
        status_stats = db.session.query(
            DownloadLog.status,
            func.count(DownloadLog.id).label('count')
        ).join(User).join(Document)
        
        # Applica stessi filtri
        if validated_filters.get('from'):
            status_stats = status_stats.filter(DownloadLog.timestamp >= validated_filters['from'])
        if validated_filters.get('to'):
            status_stats = status_stats.filter(DownloadLog.timestamp <= validated_filters['to'])
        if validated_filters.get('user_id'):
            status_stats = status_stats.filter(DownloadLog.user_id == validated_filters['user_id'])
        if validated_filters.get('username'):
            status_stats = status_stats.filter(User.username.ilike(f"%{validated_filters['username']}%"))
        if validated_filters.get('filename'):
            status_stats = status_stats.filter(Document.filename.ilike(f"%{validated_filters['filename']}%"))
        if validated_filters.get('ip'):
            status_stats = status_stats.filter(DownloadLog.ip_address.ilike(f"%{validated_filters['ip']}%"))
        if validated_filters.get('status'):
            status_stats = status_stats.filter(DownloadLog.status == validated_filters['status'])
        if validated_filters.get('source'):
            status_stats = status_stats.filter(DownloadLog.source == validated_filters['source'])
        
        status_stats = status_stats.group_by(DownloadLog.status).all()
        
        return {
            'total_count': total_count,
            'status_breakdown': {status: count for status, count in status_stats},
            'filters_applied': validated_filters
        }


# Istanza globale del servizio
download_export_service = DownloadExportService()


def rate_limit_export(f):
    """
    Decorator per rate limiting degli export.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask_login import current_user
        
        if not download_export_service.check_rate_limit(current_user.id):
            from flask import jsonify
            return jsonify({
                'error': 'Rate limit exceeded',
                'message': f'Maximum {download_export_service.rate_limit_max} exports per {download_export_service.rate_limit_window} seconds'
            }), 429
        
        return f(*args, **kwargs)
    return decorated_function
