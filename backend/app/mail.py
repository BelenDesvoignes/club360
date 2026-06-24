# api/backend/app/mail.py
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

async def send_reset_code(email: str, code: str):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Código de recuperación - CLUB360"
    msg["From"] = f"CLUB360 <{GMAIL_USER}>"
    msg["To"] = email

    html = f"""
        <h2>Recuperación de contraseña</h2>
        <p>Tu código de verificación es:</p>
        <h1 style="letter-spacing: 8px; color: #ff6f00;">{code}</h1>
        <p>Válido por <strong>10 minutos</strong>.</p>
    """
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_USER, email, msg.as_string())

async def send_shift_cancellation(email: str, nombre: str, actividad: str, fecha: str, hora: str):
    """Notificación para cancelación de una clase puntual."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Clase cancelada - CLUB360"
    msg["From"] = f"CLUB360 <{GMAIL_USER}>"
    msg["To"] = email

    html = f"""
        <h2>Hola {nombre}, te informamos que una clase fue cancelada.</h2>
        <p>La clase de <strong>{actividad}</strong> del día <strong>{fecha}</strong>
        a las <strong>{hora}</strong> hs fue cancelada.</p>
        <p>Si realizaste un pago, se te acreditará un crédito para usar en tu próxima reserva.</p>
        <p>Disculpá los inconvenientes.</p>
        <br>
        <p>— El equipo de CLUB360</p>
    """
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_USER, email, msg.as_string())


async def send_template_cancellation(email: str, nombre: str, actividad: str, dia: str, hora: str):
    """Notificación para cancelación definitiva de un turno completo."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Turno cancelado definitivamente - CLUB360"
    msg["From"] = f"CLUB360 <{GMAIL_USER}>"
    msg["To"] = email

    html = f"""
        <h2>Hola {nombre}, te informamos que un turno fue cancelado definitivamente.</h2>
        <p>El turno de <strong>{actividad}</strong> los días <strong>{dia}</strong>
        a las <strong>{hora}</strong> hs fue dado de baja.</p>
        <p>Si tenías reservas pagas en ese turno, se te acreditará el saldo correspondiente.</p>
        <p>Disculpá los inconvenientes.</p>
        <br>
        <p>— El equipo de CLUB360</p>
    """
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_USER, email, msg.as_string())

async def send_price_update(email: str, nombre: str, actividad: str, nuevo_precio: float):
    """Notificación para actualización de precio de una actividad."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Actualización de precio - {actividad}"
    msg["From"] = f"CLUB360 <{GMAIL_USER}>"
    msg["To"] = email

    html = f"""
        <h2>Hola {nombre},</h2>
        <p>Te informamos que el precio de la actividad <strong>{actividad}</strong> ha sido actualizado.</p>
        <p>El nuevo precio es: <strong>${nuevo_precio:.2f}</strong>.</p>
        <br>
        <p>— El equipo de CLUB360</p>
    """
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_USER, email, msg.as_string())