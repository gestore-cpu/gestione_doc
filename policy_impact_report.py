from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, JSON, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from extensions import db

class PolicyImpactReport(db.Model):
    """
    Report AI di impatto delle policy attive.
    Generato mensilmente per analizzare l'efficacia delle decisioni automatiche.
    """
    __tablename__ = 'policy_impact_reports'
    
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    
    # Statistiche quantitative
    total_auto_processed = Column(Integer, nullable=False, default=0)
    approve_count = Column(Integer, nullable=False, default=0)
    deny_count = Column(Integer, nullable=False, default=0)
    success_rate = Column(Float, nullable=False, default=0.0)
    
    # Analisi AI
    ai_analysis = Column(Text, nullable=False)
    
    # Dettagli aggiuntivi
    policy_breakdown = Column(JSON, nullable=True)  # Statistiche per policy
    error_cases = Column(JSON, nullable=True)  # Casi di errore identificati
    recommendations = Column(JSON, nullable=True)  # Raccomandazioni AI
    
    # Metadati
    period_start = Column(DateTime, nullable=False)  # Inizio periodo analizzato
    period_end = Column(DateTime, nullable=False)  # Fine periodo analizzato
    processing_time = Column(Float, nullable=True)  # Tempo di elaborazione in secondi
    
    # Status
    reviewed = Column(Boolean, nullable=False, default=False)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    admin_notes = Column(Text, nullable=True)
    
    # Relazioni
    reviewer = relationship('User', foreign_keys=[reviewed_by], backref='reviewed_impact_reports')
    
    def get_success_rate_display(self):
        """Restituisce il tasso di successo formattato."""
        return f"{self.success_rate:.1f}%"
    
    def get_period_display(self):
        """Restituisce il periodo analizzato formattato."""
        start = self.period_start.strftime('%d/%m/%Y')
        end = self.period_end.strftime('%d/%m/%Y')
        return f"{start} - {end}"
    
    def get_processing_time_display(self):
        """Restituisce il tempo di elaborazione formattato."""
        if self.processing_time:
            return f"{self.processing_time:.2f}s"
        return "N/A"
    
    def get_status_display(self):
        """Restituisce lo status del report."""
        if self.reviewed:
            return "📋 Revisionato"
        return "⏳ In attesa"
    
    def get_summary(self):
        """Restituisce un riassunto del report."""
        return {
            'total_requests': self.total_auto_processed,
            'approvals': self.approve_count,
            'denials': self.deny_count,
            'success_rate': self.success_rate,
            'period': self.get_period_display(),
            'status': self.get_status_display()
        }
    
    def get_policy_breakdown_summary(self):
        """Restituisce un riassunto delle statistiche per policy."""
        if not self.policy_breakdown:
            return []
        
        return [
            {
                'policy_id': item.get('policy_id'),
                'policy_name': item.get('policy_name', 'Policy #' + str(item.get('policy_id', 'N/A'))),
                'requests_processed': item.get('requests_processed', 0),
                'success_rate': item.get('success_rate', 0.0),
                'action': item.get('action', 'unknown')
            }
            for item in self.policy_breakdown
        ]
    
    def get_error_cases_summary(self):
        """Restituisce un riassunto dei casi di errore."""
        if not self.error_cases:
            return []
        
        return [
            {
                'type': item.get('type', 'unknown'),
                'count': item.get('count', 0),
                'description': item.get('description', ''),
                'examples': item.get('examples', [])
            }
            for item in self.error_cases
        ]
    
    def get_recommendations_summary(self):
        """Restituisce un riassunto delle raccomandazioni."""
        if not self.recommendations:
            return []
        
        return [
            {
                'type': item.get('type', 'unknown'),
                'priority': item.get('priority', 'medium'),
                'description': item.get('description', ''),
                'impact': item.get('impact', 'unknown')
            }
            for item in self.recommendations
        ]
    
    def mark_as_reviewed(self, admin_notes, user_id):
        """Marca il report come revisionato."""
        self.reviewed = True
        self.reviewed_at = datetime.utcnow()
        self.reviewed_by = user_id
        self.admin_notes = admin_notes
    
    @classmethod
    def get_latest_report(cls):
        """Restituisce l'ultimo report generato."""
        return cls.query.order_by(cls.created_at.desc()).first()
    
    @classmethod
    def get_reports_statistics(cls):
        """Restituisce statistiche sui report."""
        total_reports = cls.query.count()
        reviewed_reports = cls.query.filter_by(reviewed=True).count()
        avg_success_rate = db.session.query(func.avg(cls.success_rate)).scalar() or 0.0
        
        return {
            'total_reports': total_reports,
            'reviewed_reports': reviewed_reports,
            'pending_reports': total_reports - reviewed_reports,
            'avg_success_rate': avg_success_rate
        }
    
    @classmethod
    def get_recent_reports(cls, limit=10):
        """Restituisce i report più recenti."""
        return cls.query.order_by(cls.created_at.desc()).limit(limit).all() 