from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, SubmitField, FileField,
    SelectField, SelectMultipleField, TextAreaField, BooleanField
)
from wtforms.validators import DataRequired, Optional, Email, Length, EqualTo


# === FORM LOGIN ===
class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Ricordami')
    submit = SubmitField('Accedi')


# === FORM RESET PASSWORD (richiesta via email) ===
class ResetPasswordForm(FlaskForm):
    email = StringField('Indirizzo Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Invia email di reset')


# === FORM RESET CON TOKEN ===
class ResetWithTokenForm(FlaskForm):
    new_password = PasswordField('Nuova Password', validators=[
        DataRequired(),
        Length(min=8, message="La nuova password deve contenere almeno 8 caratteri.")
    ])
    confirm_password = PasswordField('Conferma Password', validators=[
        DataRequired(),
        EqualTo('new_password', message='Le password devono coincidere.')
    ])
    submit = SubmitField('Aggiorna password')


# === FORM UPLOAD DOCUMENTI ===
class UploadForm(FlaskForm):
    title = StringField('Titolo', validators=[DataRequired()])
    description = StringField('Descrizione', validators=[Optional()])
    file = FileField('Documento', validators=[DataRequired()])
    visibility = SelectField('Visibilità', choices=[
        ('privato', 'Privato'),
        ('protetto', 'Protetto da password'),
        ('condividi', 'Condiviso via email'),
        ('aziendale', 'Visibile a tutti'),
        ('reparto', 'Visibile solo reparto')
    ], validators=[DataRequired()])
    password = PasswordField('Password', validators=[Optional()])
    shared_email = StringField('Email destinatari', validators=[Optional(), Email()])
    target_companies = SelectMultipleField('Aziende', coerce=int)
    target_departments = SelectMultipleField('Reparti', coerce=int)
    destination = SelectField('Dove salvare', choices=[
        ('local', 'Su server locale'),
        ('gdrive', 'Su Google Drive')
    ], validators=[DataRequired()])
    submit = SubmitField('Carica')


# === FORM CAMBIO PASSWORD ===
class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('Vecchia Password', validators=[DataRequired()])
    new_password = PasswordField('Nuova Password', validators=[
        DataRequired(),
        Length(min=8, message="La nuova password deve contenere almeno 8 caratteri.")
    ])
    submit = SubmitField('Aggiorna')


# === FORM SEGNALAZIONE (Problema o Suggerimento) ===
class SegnalazioneForm(FlaskForm):
    message = TextAreaField('Messaggio', validators=[DataRequired()])
    submit = SubmitField('Invia')


# === FORM CREAZIONE UTENTE (admin only) ===
class CreateUserForm(FlaskForm):
    username = StringField('Nome utente', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8, message="La password deve contenere almeno 8 caratteri.")
    ])
    role = SelectField('Ruolo', choices=[
        ('user', 'User'),
        ('guest', 'Guest'),
        ('admin', 'Admin')
    ], validators=[DataRequired()])
    submit = SubmitField('Crea Utente')

# === FORM ACCESSO OSPITE ===
class GuestAccessForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Accedi come Ospite')

# === FORM REGISTRAZIONE OSPITE ===
class GuestRegisterForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8, message="La password deve contenere almeno 8 caratteri.")
    ])
    confirm = PasswordField('Conferma Password', validators=[
        DataRequired(),
        EqualTo('password', message='Le password devono coincidere.')
    ])
    submit = SubmitField('Registrati')
