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


def _format_date_ddmmyyyy(value: str | None) -> str | None:
    if not value:
        return None

    raw = str(value).strip()
    parts = raw.split("T")[0].split("-")
    if len(parts) != 3:
        return raw

    year, month, day = parts
    if len(year) != 4 or len(month) != 2 or len(day) != 2:
        return raw

    return f"{day}/{month}/{year}"

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

    with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as server:
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

    with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as server:
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

    with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as server:
        server.starttls()
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_USER, email, msg.as_string())


async def send_subscription_payment_reminder(
    email: str,
    nombre: str,
    deporte: str,
    vencimiento: str | None = None,
):
    """Recordatorio de último día para pagar un abono pendiente."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Último día para pagar tu abono de {deporte} - CLUB360"
    msg["From"] = f"CLUB360 <{GMAIL_USER}>"
    msg["To"] = email

    formatted_due_date = _format_date_ddmmyyyy(vencimiento)
    vencimiento_html = (
        f"<p>Fecha límite de pago: <strong>{formatted_due_date}</strong>.</p>"
        if formatted_due_date
        else ""
    )

    html = f"""
        <h2>Hola {nombre}, hoy es tu último día para pagar tu abono de {deporte}.</h2>
        <p>Si no completás el pago hoy, tu reserva puede quedar suspendida hasta regularizar la deuda.</p>
        {vencimiento_html}
        <p>Podés hacerlo desde la sección de <strong>Mis Pagos</strong> dentro de CLUB360.</p>
        <p>Gracias por usar CLUB360.</p>
    """
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as server:
        server.starttls()
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_USER, email, msg.as_string())