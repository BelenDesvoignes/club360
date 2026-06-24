# api/backend/app/mail.py
import asyncio
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")


def _send_message_sync(to_email: str, msg: MIMEMultipart):
    with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as server:
        server.starttls()
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_USER, to_email, msg.as_string())


async def _send_message(to_email: str, msg: MIMEMultipart):
    await asyncio.to_thread(_send_message_sync, to_email, msg)


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

    await _send_message(email, msg)

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

    await _send_message(email, msg)


async def send_waitlist_promotion_offer(
    email: str, 
    nombre: str, 
    actividad: str, 
    fecha: str, 
    hora: str, 
    token: str,
    frontend_url: str = "http://localhost:5173"
):
    """Notificación de que el usuario fue promovido en la lista de espera."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "¡Hay un cupo disponible! - CLUB360"
    msg["From"] = f"CLUB360 <{GMAIL_USER}>"
    msg["To"] = email

    offer_link = f"{frontend_url}/waitlist-accept/{token}"

    html = f"""
        <h2>¡Hola {nombre}!</h2>
        <p>Se liberó un cupo en la clase que solicitaste. ¡Tenés una oportunidad!</p>
        
        <p>
            <strong>Actividad:</strong> {actividad}<br>
            <strong>Fecha:</strong> {fecha}<br>
            <strong>Horario:</strong> {hora} hs
        </p>
        
        <p>Esta oferta es válida por <strong>24 horas</strong>. Si no respondes en ese tiempo, 
        pasaremos al siguiente en la lista de espera.</p>
        
        <div style="margin: 20px 0;">
            <a href="{offer_link}" style="
                display: inline-block; 
                background-color: #5a8849; 
                color: white; 
                padding: 12px 24px; 
                border-radius: 8px; 
                text-decoration: none; 
                font-weight: bold;
            ">
                Ingresar a CLUB360
            </a>
        </div>
        
        <p style="font-size: 12px; color: #6b7280;">
            Si tenés problemas con los enlaces, podés responder a este email o contactar 
            directamente a soporte en CLUB360.
        </p>
        
        <p>— El equipo de CLUB360</p>
    """
    msg.attach(MIMEText(html, "html"))

    await _send_message(email, msg)


async def send_template_cancellation(email: str, nombre: str, actividad: str, dia: str, hora: str):
    """Notificación para cancelación definitiva de un turno completo."""
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

    await _send_message(email, msg)


async def send_admin_waitlist_alert(admin_email: str, instance_id: int, count: int, actividad: str, fecha: str, hora: str):
    """Notificación para los administradores cuando una lista de espera alcanza o supera las 10 personas."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Lista de espera con 10 inscripciones - CLUB360"
    msg["From"] = f"CLUB360 <{GMAIL_USER}>"
    msg["To"] = admin_email

    html = f"""
        <h2>Alerta de alta demanda - CLUB360</h2>
        <p>Te informamos que la lista de espera para una clase ha alcanzado las 10 inscripciones.</p>
        
        <div style="background-color: #fff7ed; border-left: 5px solid #ff6f00; padding: 15px; margin: 20px 0; border-radius: 4px;">
            <strong style="color: #b45309; font-size: 1.1rem;">Detalles del Turno:</strong><br>
            <p style="margin: 5px 0; color: #4b5563;">
                <strong>Actividad:</strong> {actividad}<br>
                <strong>Fecha:</strong> {fecha}<br>
                <strong>Horario:</strong> {hora} hs<br>
                <strong>Inscriptos en espera:</strong> <span style="font-weight: 800; color: #dc2626;">{count} usuarios</span>
            </p>
        </div>
        
        <p> Considerá evaluar la apertura de un nuevo turno o ampliar el cupo de la clase si la tendencia se mantiene.</p>
        <br>
        <p style="font-size: 12px; color: #9ca3af;">— Sistema de Alertas Automáticas CLUB360</p>
    """
    msg.attach(MIMEText(html, "html"))

    await _send_message(admin_email, msg)
