import logging

import resend

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    @staticmethod
    def _send(to_email: str, subject: str, html_body: str) -> bool:
        if not settings.RESEND_API_KEY:
            logger.warning(f"RESEND_API_KEY no configurado. Email no enviado a {to_email}")
            return False
        try:
            resend.api_key = settings.RESEND_API_KEY
            response = resend.Emails.send({
                "from": f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM_ADDRESS}>",
                "to": [to_email],
                "subject": subject,
                "html": html_body,
            })
            logger.info(f"Email enviado via Resend a {to_email} | id={response.get('id')} | {subject}")
            return True
        except Exception as e:
            logger.error(f"Error enviando email a {to_email}: {e}")
            return False

    @staticmethod
    def send_reset_password(to_email: str, nombre: str, codigo: str) -> bool:
        """Codigo de 6 digitos para restablecer la contraseña, expira en 15 min."""
        subject = "Código para restablecer tu contraseña - HablaVas"
        html = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family: Arial, sans-serif; background:#f4f4f4; padding:20px;">
          <div style="max-width:600px; margin:auto; background:#fff; border-radius:8px; overflow:hidden;">
            <div style="background:#141414; padding:24px; text-align:center;">
              <h1 style="color:#F5B800; margin:0;">🛵 HablaVas</h1>
            </div>
            <div style="padding:32px;">
              <h2 style="color:#333;">Hola, {nombre}</h2>
              <p style="color:#555; font-size:16px; line-height:1.6;">
                Recibimos una solicitud para restablecer tu contraseña. Usa este código:
              </p>
              <div style="text-align:center; margin:32px 0;">
                <div style="background:#f8f8f8; border:2px dashed #F5B800;
                            border-radius:8px; padding:24px; display:inline-block;">
                  <span style="font-size:42px; font-weight:bold;
                               letter-spacing:12px; color:#141414;">{codigo}</span>
                </div>
              </div>
              <p style="color:#555; font-size:14px; text-align:center;">
                Este código expira en <strong>15 minutos</strong>.
              </p>
              <p style="color:#999; font-size:13px; text-align:center; margin-top:24px;">
                Si no solicitaste esto, ignora este correo.
              </p>
              <hr style="border:none; border-top:1px solid #eee; margin:24px 0;">
              <p style="color:#999; font-size:12px; text-align:center;">
                {settings.EMAIL_FROM_NAME} · {settings.EMAIL_FROM_ADDRESS}
              </p>
            </div>
          </div>
        </body>
        </html>
        """
        return EmailService._send(to_email, subject, html)


email_service = EmailService()
