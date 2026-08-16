from decouple import config
from typing import List


class Settings:
    DATABASE_URL: str = config("DATABASE_URL")
    SECRET_KEY: str = config("SECRET_KEY", default="cambiar-en-produccion-ubermotor")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 12  # turno largo: 12 horas

    # CORS: NO usar "*" con allow_credentials=True (el navegador lo rechaza).
    # Lista explicita de origenes permitidos. En Railway se configura la
    # variable CORS_ORIGINS separada por comas (default: front + localhost).
    CORS_ORIGINS: List[str] = config(
        "CORS_ORIGINS",
        default="https://appfrontubermotor-production.up.railway.app,http://localhost:8080,http://localhost:3000",
        cast=lambda v: [o.strip() for o in v.split(",") if o.strip()],
    )

    # ImageKit (fotos y documentos del conductor)
    IMAGEKIT_PUBLIC_KEY: str = config("IMAGEKIT_PUBLIC_KEY", default="")
    IMAGEKIT_PRIVATE_KEY: str = config("IMAGEKIT_PRIVATE_KEY", default="")
    IMAGEKIT_URL_ENDPOINT: str = config("IMAGEKIT_URL_ENDPOINT", default="")

    # SOS: webhook al sistema de Serenazgo/Policia. Mientras no haya endpoint
    # real, se deja vacio y la alerta queda registrada en la BD.
    POLICIA_WEBHOOK_URL: str = config("POLICIA_WEBHOOK_URL", default="")
    # Credenciales del webhook externo (Basic Auth: usuario + clave).
    POLICIA_WEBHOOK_USUARIO: str = config("POLICIA_WEBHOOK_USUARIO", default="")
    POLICIA_WEBHOOK_CLAVE: str = config("POLICIA_WEBHOOK_CLAVE", default="")
    SOS_CONFIRMACIONES: int = 2  # veces que se presiona el boton para activar

    # Tarifa mínima por carrera (soles) que el cliente le paga al conductor
    TARIFA_MINIMA_CARRERA: float = 3.0
    # Rechazos del conductor que disparan el descuento de saldo
    RECHAZOS_PARA_DESCUENTO: int = 3

    # Resend (recuperacion de contraseña por correo)
    RESEND_API_KEY: str = config("RESEND_API_KEY", default="")
    EMAIL_FROM_ADDRESS: str = config("EMAIL_FROM_ADDRESS", default="sistemas@jsinnovatech.com")
    EMAIL_FROM_NAME: str = config("EMAIL_FROM_NAME", default="UberMotor")

    # Geoapify (geocodificacion: autocompletado de direcciones + reverse).
    # La key vive en el BACKEND para no exponerla en el front.
    GEOAPIFY_KEY: str = config("GEOAPIFY_KEY", default="")

    # OneSignal (notificaciones push: despiertan el telefono aunque la app este
    # cerrada o en segundo plano). El app_id va tambien en el front (dart-define),
    # la REST API Key SOLO vive aca en el backend.
    ONESIGNAL_APP_ID: str = config("ONESIGNAL_APP_ID", default="")
    ONESIGNAL_REST_API_KEY: str = config("ONESIGNAL_REST_API_KEY", default="")

    # Google Sign-In: Web Client ID del proyecto (Google Cloud Console /
    # Firebase). Se usa para validar el campo "aud" del id_token que manda
    # el front, y confirmar que el token es realmente para esta app.
    GOOGLE_CLIENT_ID: str = config("GOOGLE_CLIENT_ID", default="")


settings = Settings()
