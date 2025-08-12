"""
Servizio per la generazione automatica del report PDF mensile del CEO.
Include invii PDF sensibili, alert AI attivi e audit trail events.
"""

import os
import logging
from datetime import datetime, timedelta
from calendar import monthrange
from flask import current_app
from flask_mail import Message
from extensions import db, mail
from models import LogInvioPDF, NotificaCEO, AlertAI, AuditLog, AdminLog, User, Document, GuestActivity, AlertReportCEO
from sqlalchemy import func, and_, or_
import json
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from io import BytesIO
import tempfile

logger = logging.getLogger(__name__)

class CEOMonthlyReportGenerator:
    """
    Generatore di report PDF mensili per il CEO.
    """
    
    def __init__(self, month=None, year=None):
        """
        Inizializza il generatore di report.
        
        Args:
            month (int): Mese del report (1-12). Se None, usa il mese precedente.
            year (int): Anno del report. Se None, usa l'anno corrente.
        """
        if month is None or year is None:
            # Calcola il mese precedente
            today = datetime.now()
            if today.month == 1:
                self.month = 12
                self.year = today.year - 1
            else:
                self.month = today.month - 1
                self.year = today.year
        else:
            self.month = month
            self.year = year
            
        # Calcola le date di inizio e fine mese
        _, last_day = monthrange(self.year, self.month)
        self.start_date = datetime(self.year, self.month, 1)
        self.end_date = datetime(self.year, self.month, last_day, 23, 59, 59)
        
        # Nomi dei mesi in italiano
        self.month_names = {
            1: 'Gennaio', 2: 'Febbraio', 3: 'Marzo', 4: 'Aprile',
            5: 'Maggio', 6: 'Giugno', 7: 'Luglio', 8: 'Agosto',
            9: 'Settembre', 10: 'Ottobre', 11: 'Novembre', 12: 'Dicembre'
        }
        
    def get_sensitive_pdf_sends(self):
        """
        Recupera gli invii PDF sensibili del mese.
        
        Returns:
            list: Lista di LogInvioPDF sensibili
        """
        try:
            # Criteri per PDF sensibili:
            # 1. Mittente è admin
            # 2. Destinatario ha alert AI alto/critico
            # 3. Destinatario è guest con scadenza < 3 giorni
            # 4. Destinatario ha email non aziendale
            
            # Query base per invii PDF del mese
            base_query = LogInvioPDF.query.filter(
                and_(
                    LogInvioPDF.timestamp >= self.start_date,
                    LogInvioPDF.timestamp <= self.end_date,
                    LogInvioPDF.inviato_da.like('%admin%')  # Mittente admin
                )
            )
            
            sensitive_sends = []
            
            for log_entry in base_query.all():
                is_sensitive = False
                trigger_criterion = ""
                
                # Verifica se destinatario ha alert AI alto/critico
                if log_entry.tipo == 'user':
                    user = User.query.get(log_entry.id_utente_o_guest)
                    if user:
                        high_alerts = AlertAI.query.filter(
                            and_(
                                AlertAI.user_id == user.id,
                                AlertAI.livello.in_(['alto', 'critico']),
                                AlertAI.stato == 'nuovo'
                            )
                        ).count()
                        if high_alerts > 0:
                            is_sensitive = True
                            trigger_criterion = f"Alert AI {high_alerts} alto/critico"
                
                # Verifica se destinatario è guest con scadenza < 3 giorni
                elif log_entry.tipo == 'guest':
                    guest = User.query.filter_by(id=log_entry.id_utente_o_guest, role='guest').first()
                    if guest and guest.access_expiration:
                        days_to_expiry = (guest.access_expiration - datetime.now().date()).days
                        if days_to_expiry < 3:
                            is_sensitive = True
                            trigger_criterion = f"Scadenza accesso in {days_to_expiry} giorni"
                
                # Verifica email non aziendale
                if not log_entry.inviato_a.endswith('@mercurysurgelati.org'):
                    is_sensitive = True
                    trigger_criterion = "Email esterna"
                
                if is_sensitive:
                    log_entry.trigger_criterion = trigger_criterion
                    sensitive_sends.append(log_entry)
            
            return sensitive_sends
            
        except Exception as e:
            logger.error(f"❌ Errore recupero invii PDF sensibili: {e}")
            return []
    
    def get_critical_pdf_sends(self):
        """
        Recupera gli invii PDF critici del mese (criteri più stringenti).
        
        Returns:
            list: Lista di LogInvioPDF critici
        """
        try:
            critical_sends = []
            
            # Query base per invii PDF del mese
            base_query = LogInvioPDF.query.filter(
                and_(
                    LogInvioPDF.timestamp >= self.start_date,
                    LogInvioPDF.timestamp <= self.end_date
                )
            )
            
            for log_entry in base_query.all():
                is_critical = False
                critical_reason = ""
                
                # Criterio 1: Email esterna non registrata come utente
                if not log_entry.inviato_a.endswith('@mercurysurgelati.org'):
                    # Verifica se l'email è registrata come utente
                    user_exists = User.query.filter_by(email=log_entry.inviato_a).first()
                    if not user_exists:
                        is_critical = True
                        critical_reason = "Email esterna non registrata"
                
                # Criterio 2: Destinatario con alert AI attivo
                if log_entry.tipo == 'user':
                    user = User.query.get(log_entry.id_utente_o_guest)
                    if user:
                        active_alerts = AlertAI.query.filter(
                            and_(
                                AlertAI.user_id == user.id,
                                AlertAI.stato.in_(['nuovo', 'in_revisione'])
                            )
                        ).count()
                        if active_alerts > 0:
                            is_critical = True
                            critical_reason = f"Utente con {active_alerts} alert AI attivi"
                
                # Criterio 3: Download multipli nelle 24h successive
                # (Implementazione semplificata - in produzione andrebbe verificato)
                # Per ora consideriamo critici gli invii a guest
                elif log_entry.tipo == 'guest':
                    is_critical = True
                    critical_reason = "Invio a guest (potenziale download multiplo)"
                
                # Criterio 4: Documento marcato come sensibile
                # (Implementazione futura - campo nel DB)
                
                if is_critical:
                    log_entry.critical_reason = critical_reason
                    critical_sends.append(log_entry)
            
            return critical_sends
            
        except Exception as e:
            logger.error(f"❌ Errore recupero invii PDF critici: {e}")
            return []
    
    def check_and_create_report_alert(self, report_filename):
        """
        Verifica se creare un alert per il report e lo crea se necessario.
        
        Args:
            report_filename (str): Nome del file report generato
            
        Returns:
            AlertReportCEO or None: L'alert creato o None se non necessario
        """
        try:
            # Ottieni invii critici
            critical_sends = self.get_critical_pdf_sends()
            num_critical = len(critical_sends)
            
            logger.info(f"📊 Report {self.month}/{self.year}: {num_critical} invii critici rilevati")
            
            # Verifica se creare alert (≥ 3 invii critici)
            if num_critical >= 3:
                # Verifica se esiste già un alert per questo periodo
                existing_alert = AlertReportCEO.get_alert_attivo_per_periodo(self.month, self.year)
                
                if existing_alert:
                    # Aggiorna alert esistente
                    existing_alert.numero_invii_critici = num_critical
                    existing_alert.data_trigger = datetime.utcnow()
                    existing_alert.id_report_ceo = report_filename
                    existing_alert.note = f"Aggiornato: {num_critical} invii critici rilevati"
                    db.session.commit()
                    
                    logger.info(f"⚠️ Alert aggiornato per {self.month}/{self.year}: {num_critical} critici")
                    return existing_alert
                else:
                    # Crea nuovo alert
                    alert = AlertReportCEO(
                        mese=self.month,
                        anno=self.year,
                        numero_invii_critici=num_critical,
                        trigger_attivo=True,
                        data_trigger=datetime.utcnow(),
                        id_report_ceo=report_filename,
                        letto=False,
                        note=f"Alert automatico: {num_critical} invii critici rilevati nel report mensile"
                    )
                    
                    db.session.add(alert)
                    db.session.commit()
                    
                    logger.warning(f"🚨 NUOVO ALERT CREATO per {self.month}/{self.year}: {num_critical} invii critici!")
                    return alert
            else:
                logger.info(f"✅ Nessun alert necessario: {num_critical} invii critici (soglia: 3)")
                return None
                
        except Exception as e:
            logger.error(f"❌ Errore verifica alert report: {e}")
            return None
    
    def get_active_ai_alerts(self):
        """
        Recupera gli alert AI attivi del mese.
        
        Returns:
            list: Lista di AlertAI attivi
        """
        try:
            alerts = AlertAI.query.filter(
                and_(
                    AlertAI.created_at >= self.start_date,
                    AlertAI.created_at <= self.end_date,
                    AlertAI.livello.in_(['alto', 'critico']),
                    AlertAI.stato.in_(['nuovo', 'in_revisione'])
                )
            ).order_by(AlertAI.created_at.desc()).all()
            
            return alerts
            
        except Exception as e:
            logger.error(f"❌ Errore recupero alert AI: {e}")
            return []
    
    def get_audit_trail_events(self):
        """
        Recupera gli eventi di audit trail del mese.
        
        Returns:
            list: Lista di eventi di audit
        """
        try:
            # Eventi di audit trail
            audit_events = []
            
            # 1. Modifiche permessi (AdminLog)
            permission_mods = AdminLog.query.filter(
                and_(
                    AdminLog.timestamp >= self.start_date,
                    AdminLog.timestamp <= self.end_date,
                    AdminLog.action.like('%permission%')
                )
            ).all()
            
            for log in permission_mods:
                audit_events.append({
                    'timestamp': log.timestamp,
                    'event_type': 'Modifica Permessi',
                    'user': log.performed_by,
                    'action': log.action,
                    'user_role': 'Admin'
                })
            
            # 2. Creazione/eliminazione documenti
            doc_events = AdminLog.query.filter(
                and_(
                    AdminLog.timestamp >= self.start_date,
                    AdminLog.timestamp <= self.end_date,
                    or_(
                        AdminLog.action.like('%create%'),
                        AdminLog.action.like('%delete%'),
                        AdminLog.action.like('%upload%')
                    )
                )
            ).all()
            
            for log in doc_events:
                audit_events.append({
                    'timestamp': log.timestamp,
                    'event_type': 'Gestione Documenti',
                    'user': log.performed_by,
                    'action': log.action,
                    'user_role': 'Admin'
                })
            
            # 3. Download massivi
            mass_downloads = GuestActivity.query.filter(
                and_(
                    GuestActivity.timestamp >= self.start_date,
                    GuestActivity.timestamp <= self.end_date,
                    GuestActivity.action == 'download'
                )
            ).group_by(GuestActivity.user_id).having(
                func.count(GuestActivity.id) > 5
            ).all()
            
            for activity in mass_downloads:
                user = User.query.get(activity.user_id)
                audit_events.append({
                    'timestamp': activity.timestamp,
                    'event_type': 'Download Massivo',
                    'user': user.email if user else f"Guest {activity.user_id}",
                    'action': f"Download multipli ({activity.download_count})",
                    'user_role': user.role if user else 'Guest'
                })
            
            # 4. Modifiche utenti/guest
            user_mods = AdminLog.query.filter(
                and_(
                    AdminLog.timestamp >= self.start_date,
                    AdminLog.timestamp <= self.end_date,
                    or_(
                        AdminLog.action.like('%user%'),
                        AdminLog.action.like('%guest%'),
                        AdminLog.action.like('%role%')
                    )
                )
            ).all()
            
            for log in user_mods:
                audit_events.append({
                    'timestamp': log.timestamp,
                    'event_type': 'Gestione Utenti',
                    'user': log.performed_by,
                    'action': log.action,
                    'user_role': 'Admin'
                })
            
            # Ordina per timestamp
            audit_events.sort(key=lambda x: x['timestamp'], reverse=True)
            
            return audit_events
            
        except Exception as e:
            logger.error(f"❌ Errore recupero audit trail: {e}")
            return []
    
    def generate_pdf_report(self):
        """
        Genera il report PDF mensile.
        
        Returns:
            bytes: Contenuto del PDF
        """
        try:
            # Recupera i dati
            sensitive_sends = self.get_sensitive_pdf_sends()
            active_alerts = self.get_active_ai_alerts()
            audit_events = self.get_audit_trail_events()
            
            # Crea il PDF
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            story = []
            
            # Stili
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                spaceAfter=30,
                alignment=TA_CENTER,
                textColor=colors.darkblue
            )
            
            subtitle_style = ParagraphStyle(
                'CustomSubtitle',
                parent=styles['Heading2'],
                fontSize=14,
                spaceAfter=20,
                textColor=colors.darkred
            )
            
            normal_style = styles['Normal']
            
            # Header
            story.append(Paragraph(f"Report Mensile CEO - {self.month_names[self.month]} {self.year}", title_style))
            story.append(Paragraph(f"Generato il: {datetime.now().strftime('%d/%m/%Y alle %H:%M')}", normal_style))
            story.append(Spacer(1, 20))
            
            # Sezione 1: Invii PDF Sensibili
            story.append(Paragraph("📄 Invii PDF Sensibili", subtitle_style))
            if sensitive_sends:
                # Tabella invii sensibili
                table_data = [['Data/Ora', 'Utente/Guest', 'Mittente', 'Destinatario', 'Criterio']]
                for send in sensitive_sends:
                    table_data.append([
                        send.timestamp.strftime('%d/%m/%Y %H:%M'),
                        send.nome_utente_guest,
                        send.inviato_da,
                        send.inviato_a,
                        getattr(send, 'trigger_criterion', 'N/A')
                    ])
                
                table = Table(table_data, colWidths=[1.2*inch, 1.5*inch, 1.5*inch, 1.5*inch, 1.3*inch])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.darkred),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                story.append(table)
            else:
                story.append(Paragraph("Nessun invio PDF sensibile registrato nel mese.", normal_style))
            
            story.append(Spacer(1, 20))
            
            # Sezione 2: Alert AI Attivi
            story.append(Paragraph("🤖 Alert AI Attivi", subtitle_style))
            if active_alerts:
                # Tabella alert AI
                table_data = [['Data', 'Utente/Guest', 'Tipo Alert', 'Livello', 'Stato']]
                for alert in active_alerts:
                    table_data.append([
                        alert.created_at.strftime('%d/%m/%Y'),
                        alert.utente_display,
                        alert.tipo_alert_display,
                        alert.livello_display,
                        alert.stato
                    ])
                
                table = Table(table_data, colWidths=[1*inch, 1.5*inch, 1.5*inch, 1*inch, 1*inch])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.orange),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.lightyellow),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                story.append(table)
            else:
                story.append(Paragraph("Nessun alert AI attivo registrato nel mese.", normal_style))
            
            story.append(Spacer(1, 20))
            
            # Sezione 3: Audit Trail Events
            story.append(Paragraph("🔍 Eventi Audit Trail", subtitle_style))
            if audit_events:
                # Tabella eventi audit
                table_data = [['Data/Ora', 'Tipo Evento', 'Utente', 'Azione', 'Ruolo']]
                for event in audit_events:
                    table_data.append([
                        event['timestamp'].strftime('%d/%m/%Y %H:%M'),
                        event['event_type'],
                        event['user'],
                        event['action'][:30] + '...' if len(event['action']) > 30 else event['action'],
                        event['user_role']
                    ])
                
                table = Table(table_data, colWidths=[1.2*inch, 1.3*inch, 1.3*inch, 2*inch, 1*inch])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.lightblue),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                story.append(table)
            else:
                story.append(Paragraph("Nessun evento di audit trail registrato nel mese.", normal_style))
            
            # Footer
            story.append(Spacer(1, 30))
            story.append(Paragraph("Report generato automaticamente dal sistema Mercury Docs", normal_style))
            
            # Genera il PDF
            doc.build(story)
            buffer.seek(0)
            return buffer.getvalue()
            
        except Exception as e:
            logger.error(f"❌ Errore generazione PDF report: {e}")
            return None
    
    def save_report_to_file(self, filename=None):
        """
        Salva il report PDF su file.
        
        Args:
            filename (str): Nome del file. Se None, genera automaticamente.
            
        Returns:
            str: Percorso del file salvato
        """
        try:
            if filename is None:
                filename = f"report_ceo_{self.year}_{self.month:02d}.pdf"
            
            # Crea directory reports se non esiste
            reports_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'reports')
            os.makedirs(reports_dir, exist_ok=True)
            
            file_path = os.path.join(reports_dir, filename)
            
            # Genera il PDF
            pdf_content = self.generate_pdf_report()
            if pdf_content:
                with open(file_path, 'wb') as f:
                    f.write(pdf_content)
                
                logger.info(f"✅ Report PDF salvato: {file_path}")
                return file_path
            else:
                logger.error("❌ Errore: contenuto PDF vuoto")
                return None
                
        except Exception as e:
            logger.error(f"❌ Errore salvataggio report PDF: {e}")
            return None
    
    def send_report_via_email(self, ceo_email=None):
        """
        Invia il report PDF via email al CEO.
        
        Args:
            ceo_email (str): Email del CEO. Se None, usa la configurazione.
            
        Returns:
            bool: True se inviato con successo
        """
        try:
            if ceo_email is None:
                ceo_email = current_app.config.get('CEO_EMAIL') or os.getenv('CEO_EMAIL')
            
            if not ceo_email:
                logger.warning("⚠️ CEO_EMAIL non configurata, skip invio email")
                return False
            
            # Genera il PDF
            pdf_content = self.generate_pdf_report()
            if not pdf_content:
                logger.error("❌ Errore: impossibile generare PDF")
                return False
            
            # Prepara l'email
            subject = f"Report Mensile CEO - {self.month_names[self.month]} {self.year}"
            
            html_body = f"""
            <html>
            <body>
                <h2>Report Mensile CEO - {self.month_names[self.month]} {self.year}</h2>
                <p>Gentile CEO,</p>
                <p>In allegato il report mensile automatico con:</p>
                <ul>
                    <li>📄 Invii PDF sensibili</li>
                    <li>🤖 Alert AI attivi</li>
                    <li>🔍 Eventi audit trail</li>
                </ul>
                <p>Report generato automaticamente il {datetime.now().strftime('%d/%m/%Y alle %H:%M')}</p>
                <br>
                <p>Cordiali saluti,<br>Sistema Mercury Docs</p>
            </body>
            </html>
            """
            
            # Crea il messaggio
            msg = Message(
                subject=subject,
                recipients=[ceo_email],
                html=html_body
            )
            
            # Allega il PDF
            msg.attach(
                f"report_ceo_{self.year}_{self.month:02d}.pdf",
                "application/pdf",
                pdf_content
            )
            
            # Invia l'email
            mail.send(msg)
            
            logger.info(f"✅ Report inviato via email a {ceo_email}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Errore invio email report: {e}")
            return False


def genera_report_ceo_mensile(month=None, year=None, send_email=True):
    """
    Funzione principale per generare il report mensile del CEO.
    
    Args:
        month (int): Mese del report (1-12). Se None, usa il mese precedente.
        year (int): Anno del report. Se None, usa l'anno corrente.
        send_email (bool): Se inviare il report via email.
        
    Returns:
        dict: Risultato dell'operazione
    """
    try:
        logger.info(f"🔄 Avvio generazione report CEO mensile...")
        
        # Crea il generatore
        generator = CEOMonthlyReportGenerator(month, year)
        
        # Salva il report su file
        file_path = generator.save_report_to_file()
        
        if not file_path:
            return {
                'success': False,
                'error': 'Errore generazione PDF'
            }
        
        # Verifica e crea alert se necessario
        report_filename = os.path.basename(file_path)
        alert_created = generator.check_and_create_report_alert(report_filename)
        
        # Invia via email se richiesto
        email_sent = False
        if send_email:
            email_sent = generator.send_report_via_email()
        
        return {
            'success': True,
            'file_path': file_path,
            'email_sent': email_sent,
            'month': generator.month,
            'year': generator.year,
            'alert_created': alert_created is not None,
            'alert_details': {
                'id': alert_created.id if alert_created else None,
                'num_critical': alert_created.numero_invii_critici if alert_created else 0,
                'level': alert_created.livello_criticita if alert_created else None
            } if alert_created else None
        }
        
    except Exception as e:
        logger.error(f"❌ Errore generazione report CEO: {e}")
        return {
            'success': False,
            'error': str(e)
        }


def test_report_generation():
    """
    Funzione di test per la generazione del report.
    """
    try:
        from app import app
        
        with app.app_context():
            logger.info("🧪 Test generazione report CEO...")
            
            result = genera_report_ceo_mensile(send_email=False)
            
            if result['success']:
                logger.info(f"✅ Test completato: {result['file_path']}")
                return True
            else:
                logger.error(f"❌ Test fallito: {result.get('error', 'Errore sconosciuto')}")
                return False
                
    except Exception as e:
        logger.error(f"❌ Errore test report: {e}")
        return False
