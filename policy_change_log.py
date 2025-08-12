from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from extensions import db

class PolicyChangeLog(db.Model):
    """
    Log delle modifiche automatiche alle policy effettuate dall'AI.
    Traccia ogni modifica per audit e rollback.
    """
    __tablename__ = 'policy_change_logs'
    
    id = Column(Integer, primary_key=True)
    policy_id = Column(Integer, ForeignKey('auto_policies.id'), nullable=False)
    
    # Valori precedenti
    old_condition = Column(Text, nullable=True)
    old_action = Column(String(10), nullable=True)
    old_explanation = Column(Text, nullable=True)
    old_priority = Column(Integer, nullable=True)
    old_confidence = Column(Integer, nullable=True)
    
    # Nuovi valori
    new_condition = Column(Text, nullable=True)
    new_action = Column(String(10), nullable=True)
    new_explanation = Column(Text, nullable=True)
    new_priority = Column(Integer, nullable=True)
    new_confidence = Column(Integer, nullable=True)
    
    # Metadati
    changed_at = Column(DateTime, nullable=False, server_default=func.now())
    changed_by_ai = Column(Boolean, nullable=False, default=True)
    change_reason = Column(Text, nullable=True)  # Motivo della modifica
    impact_score = Column(Integer, nullable=True)  # Punteggio impatto (0-100)
    
    # Relazioni
    policy = relationship('AutoPolicy', foreign_keys=[policy_id], backref='change_logs')
    
    def get_change_summary(self):
        """Restituisce un riassunto delle modifiche."""
        changes = []
        
        if self.old_condition != self.new_condition:
            changes.append('Condizione')
        if self.old_action != self.new_action:
            changes.append('Azione')
        if self.old_explanation != self.new_explanation:
            changes.append('Spiegazione')
        if self.old_priority != self.new_priority:
            changes.append('Priorità')
        if self.old_confidence != self.new_confidence:
            changes.append('Confidenza')
        
        return ', '.join(changes) if changes else 'Nessuna modifica'
    
    def get_change_type(self):
        """Restituisce il tipo di modifica."""
        if self.old_action != self.new_action:
            return 'action_change'
        elif self.old_condition != self.new_condition:
            return 'condition_change'
        elif self.old_explanation != self.new_explanation:
            return 'explanation_change'
        elif self.old_priority != self.new_priority or self.old_confidence != self.new_confidence:
            return 'parameter_change'
        else:
            return 'unknown'
    
    def get_change_display(self):
        """Restituisce la visualizzazione della modifica."""
        change_type = self.get_change_type()
        
        if change_type == 'action_change':
            return f"Cambio azione: {self.old_action} → {self.new_action}"
        elif change_type == 'condition_change':
            return "Modifica condizione"
        elif change_type == 'explanation_change':
            return "Aggiornamento spiegazione"
        elif change_type == 'parameter_change':
            changes = []
            if self.old_priority != self.new_priority:
                changes.append(f"Priorità: {self.old_priority} → {self.new_priority}")
            if self.old_confidence != self.new_confidence:
                changes.append(f"Confidenza: {self.old_confidence}% → {self.new_confidence}%")
            return ', '.join(changes)
        else:
            return "Modifica generica"
    
    def get_impact_level(self):
        """Restituisce il livello di impatto della modifica."""
        if not self.impact_score:
            return 'unknown'
        
        if self.impact_score >= 80:
            return 'high'
        elif self.impact_score >= 50:
            return 'medium'
        else:
            return 'low'
    
    def get_impact_display(self):
        """Restituisce la visualizzazione dell'impatto."""
        level = self.get_impact_level()
        
        if level == 'high':
            return "🔴 Alto Impatto"
        elif level == 'medium':
            return "🟡 Medio Impatto"
        elif level == 'low':
            return "🟢 Basso Impatto"
        else:
            return "⚪ Impatto Sconosciuto"
    
    def get_changed_by_display(self):
        """Restituisce chi ha effettuato la modifica."""
        if self.changed_by_ai:
            return "🤖 AI Auto-Tuning"
        else:
            return "👤 Admin"
    
    def get_timestamp_display(self):
        """Restituisce il timestamp formattato."""
        return self.changed_at.strftime('%d/%m/%Y %H:%M')
    
    def get_condition_diff(self):
        """Restituisce la differenza tra vecchia e nuova condizione."""
        if self.old_condition == self.new_condition:
            return None
        
        return {
            'old': self.old_condition or 'N/A',
            'new': self.new_condition or 'N/A',
            'changed': True
        }
    
    def get_action_diff(self):
        """Restituisce la differenza tra vecchia e nuova azione."""
        if self.old_action == self.new_action:
            return None
        
        return {
            'old': self.old_action or 'N/A',
            'new': self.new_action or 'N/A',
            'changed': True
        }
    
    def get_explanation_diff(self):
        """Restituisce la differenza tra vecchia e nuova spiegazione."""
        if self.old_explanation == self.new_explanation:
            return None
        
        return {
            'old': self.old_explanation or 'N/A',
            'new': self.new_explanation or 'N/A',
            'changed': True
        }
    
    def get_priority_diff(self):
        """Restituisce la differenza tra vecchia e nuova priorità."""
        if self.old_priority == self.new_priority:
            return None
        
        return {
            'old': self.old_priority or 'N/A',
            'new': self.new_priority or 'N/A',
            'changed': True
        }
    
    def get_confidence_diff(self):
        """Restituisce la differenza tra vecchia e nuova confidenza."""
        if self.old_confidence == self.new_confidence:
            return None
        
        return {
            'old': f"{self.old_confidence}%" if self.old_confidence else 'N/A',
            'new': f"{self.new_confidence}%" if self.new_confidence else 'N/A',
            'changed': True
        }
    
    @classmethod
    def get_recent_changes(cls, limit=50):
        """Restituisce le modifiche più recenti."""
        return cls.query.order_by(cls.changed_at.desc()).limit(limit).all()
    
    @classmethod
    def get_changes_for_policy(cls, policy_id):
        """Restituisce tutte le modifiche per una policy specifica."""
        return cls.query.filter_by(policy_id=policy_id).order_by(cls.changed_at.desc()).all()
    
    @classmethod
    def get_changes_statistics(cls):
        """Restituisce statistiche sulle modifiche."""
        total_changes = cls.query.count()
        ai_changes = cls.query.filter_by(changed_by_ai=True).count()
        admin_changes = cls.query.filter_by(changed_by_ai=False).count()
        
        # Statistiche per tipo di modifica
        action_changes = cls.query.filter(
            cls.old_action != cls.new_action
        ).count()
        
        condition_changes = cls.query.filter(
            cls.old_condition != cls.new_condition
        ).count()
        
        return {
            'total_changes': total_changes,
            'ai_changes': ai_changes,
            'admin_changes': admin_changes,
            'action_changes': action_changes,
            'condition_changes': condition_changes
        }
    
    @classmethod
    def get_impact_statistics(cls):
        """Restituisce statistiche sull'impatto delle modifiche."""
        high_impact = cls.query.filter(cls.impact_score >= 80).count()
        medium_impact = cls.query.filter(
            cls.impact_score >= 50,
            cls.impact_score < 80
        ).count()
        low_impact = cls.query.filter(
            cls.impact_score >= 0,
            cls.impact_score < 50
        ).count()
        
        return {
            'high_impact': high_impact,
            'medium_impact': medium_impact,
            'low_impact': low_impact
        } 