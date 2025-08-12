"""
Modello per i report di revisione AI delle policy automatiche.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON
from sqlalchemy.sql import func
from extensions import db

class PolicyReview(db.Model):
    """Modello per i report di revisione AI delle policy."""
    
    __tablename__ = 'policy_reviews'
    
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    report = Column(Text, nullable=False)
    suggestions = Column(JSON, nullable=True)
    reviewed_by_ai = Column(Boolean, default=True)
    status = Column(String(20), default='pending')  # pending, reviewed, applied
    admin_notes = Column(Text, nullable=True)
    applied_suggestions = Column(JSON, nullable=True)
    
    def __repr__(self):
        return f'<PolicyReview {self.id} - {self.created_at}>'
    
    def get_status_display(self):
        """Restituisce lo stato per visualizzazione."""
        status_labels = {
            'pending': '⏳ In Attesa',
            'reviewed': '✅ Revisionato',
            'applied': '🔧 Applicato'
        }
        return status_labels.get(self.status, self.status)
    
    def get_suggestions_count(self):
        """Restituisce il numero di suggerimenti."""
        if self.suggestions:
            return len(self.suggestions)
        return 0
    
    def get_applied_suggestions_count(self):
        """Restituisce il numero di suggerimenti applicati."""
        if self.applied_suggestions:
            return len(self.applied_suggestions)
        return 0
    
    def get_report_summary(self):
        """Restituisce un riassunto del report."""
        if self.report:
            return self.report[:200] + "..." if len(self.report) > 200 else self.report
        return "Nessun report disponibile"
    
    def get_suggestions_summary(self):
        """Restituisce un riassunto dei suggerimenti."""
        if not self.suggestions:
            return "Nessun suggerimento"
        
        summary = []
        for i, suggestion in enumerate(self.suggestions[:3], 1):
            condition = suggestion.get('condition', 'N/A')
            action = suggestion.get('action', 'N/A')
            summary.append(f"{i}. {condition} → {action}")
        
        if len(self.suggestions) > 3:
            summary.append(f"... e altri {len(self.suggestions) - 3} suggerimenti")
        
        return "\n".join(summary)
    
    def mark_as_reviewed(self, admin_notes=None):
        """Marca il report come revisionato."""
        self.status = 'reviewed'
        if admin_notes:
            self.admin_notes = admin_notes
        db.session.commit()
    
    def apply_suggestions(self, suggestion_ids):
        """Applica i suggerimenti selezionati."""
        if not self.suggestions:
            return False
        
        applied = []
        for suggestion_id in suggestion_ids:
            if 0 <= suggestion_id < len(self.suggestions):
                applied.append(self.suggestions[suggestion_id])
        
        if applied:
            self.applied_suggestions = applied
            self.status = 'applied'
            db.session.commit()
            return True
        
        return False
    
    @classmethod
    def get_recent_reviews(cls, limit=10):
        """Recupera i report recenti."""
        return cls.query.order_by(cls.created_at.desc()).limit(limit).all()
    
    @classmethod
    def get_pending_reviews(cls):
        """Recupera i report in attesa di revisione."""
        return cls.query.filter_by(status='pending').order_by(cls.created_at.desc()).all()
    
    @classmethod
    def get_review_statistics(cls):
        """Recupera statistiche sui report."""
        total = cls.query.count()
        pending = cls.query.filter_by(status='pending').count()
        reviewed = cls.query.filter_by(status='reviewed').count()
        applied = cls.query.filter_by(status='applied').count()
        
        return {
            'total': total,
            'pending': pending,
            'reviewed': reviewed,
            'applied': applied
        } 