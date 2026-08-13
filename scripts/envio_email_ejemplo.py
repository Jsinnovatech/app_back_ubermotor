#!/usr/bin/env python3
"""
Ejemplo de envio de email con Resend (patron HablaVas).

Uso:
    python envio_email_ejemplo.py

Configura:
    RESEND_API_KEY        -> tu API key de Resend (https://resend.com/api-keys)
    EMAIL_FROM_ADDRESS    -> remitente verificado (ej. sistemas@jsinnovatech.com)
    EMAIL_FROM_NAME       -> nombre del remitente
    CORREO_DESTINO        -> a quien le llega (ej. tu@correo.com)

Si no defines las variables, el script las pide por consola.
"""
import base64
import mimetypes
import os
import sys

# ── 1. Configuracion ──────────────────────────────────────────────
try:
    import resend
except ImportError:
    sys.exit("Falta la libreria: pip install resend")

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
EMAIL_FROM_ADDRESS = os.getenv("EMAIL_FROM_ADDRESS", "sistemas@jsinnovatech.com")
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "HablaVas")
CORREO_DESTINO = os.getenv("CORREO_DESTINO", "alancairampoma@gmail.com")

if not RESEND_API_KEY:
    RESEND_API_KEY = input("RESEND_API_KEY (pega tu key de Resend): ").strip()
if not RESEND_API_KEY:
    sys.exit("Se necesita RESEND_API_KEY")


# ── 2. El email ───────────────────────────────────────────────────
ASUNTO = "🛵 HablaVas — Correo de prueba con Resend (con adjuntos)"
HTML = """
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; background:#f4f4f4; padding:20px;">
  <div style="max-width:600px; margin:auto; background:#fff; border-radius:8px; overflow:hidden;">
    <div style="background:#141414; padding:24px; text-align:center;">
      <h1 style="color:#F5B800; margin:0;">🛵 HablaVas</h1>
    </div>
    <div style="padding:32px;">
      <h2 style="color:#333;">¡Hola!</h2>
      <p style="color:#555; font-size:16px; line-height:1.6;">
        Este es un correo de prueba enviado con <strong>Resend</strong>,
        usando el mismo patrón que HablaVas usa para la recuperación de contraseña.
      </p>
      <div style="text-align:center; margin:32px 0;">
        <div style="background:#f8f8f8; border:2px dashed #F5B800;
                    border-radius:8px; padding:24px; display:inline-block;">
          <span style="font-size:36px; font-weight:bold; color:#141414;">HablaVas</span>
        </div>
      </div>
      <p style="color:#555; font-size:14px; text-align:center;">
        MotoTaxi ride-hailing · prepago de carreras · SOS · tracking en vivo
      </p>
      <hr style="border:none; border-top:1px solid #eee; margin:24px 0;">
      <p style="color:#999; font-size:12px; text-align:center;">
        Enviado desde el script de ejemplo <code>envio_email_ejemplo.py</code>
      </p>
    </div>
  </div>
</body>
</html>
"""


# ── 3. Adjuntos (opcional) ────────────────────────────────────────
# Pasa la ruta de un archivo en ADJUNTOS (separados por coma) y se envia
# como base64. Ejemplo:
#   ADJUNTOS="diagramas/HablaVas_diagramas.docx,ARQUITECTURA_BACKEND.md"
ADJUNTOS = os.getenv("ADJUNTOS", "").split(",")


def _adjuntos_payload() -> list[dict]:
    """Convierte las rutas en la lista 'attachments' que espera Resend."""
    payload = []
    for ruta in ADJUNTOS:
        ruta = ruta.strip()
        if not ruta or not os.path.exists(ruta):
            continue
        with open(ruta, "rb") as f:
            contenido = f.read()
        nombre = os.path.basename(ruta)
        mime, _ = mimetypes.guess_type(ruta)
        payload.append({
            "filename": nombre,
            "content": base64.b64encode(contenido).decode(),
            "content_type": mime or "application/octet-stream",
        })
    return payload


# ── 4. Envio ──────────────────────────────────────────────────────
def main() -> None:
    resend.api_key = RESEND_API_KEY

    print(f"Enviando a: {CORREO_DESTINO}")
    print(f"De: {EMAIL_FROM_NAME} <{EMAIL_FROM_ADDRESS}>")
    print(f"Asunto: {ASUNTO}")

    adjuntos = _adjuntos_payload()
    if adjuntos:
        print(f"Adjuntos: {[a['filename'] for a in adjuntos]}")

    try:
        mensaje = {
            "from": f"{EMAIL_FROM_NAME} <{EMAIL_FROM_ADDRESS}>",
            "to": [CORREO_DESTINO],
            "subject": ASUNTO,
            "html": HTML,
        }
        if adjuntos:
            mensaje["attachments"] = adjuntos
        response = resend.Emails.send(mensaje)
        print(f"\n✅ Email enviado. ID: {response.get('id')}")
    except Exception as e:
        print(f"\n❌ Error al enviar: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
