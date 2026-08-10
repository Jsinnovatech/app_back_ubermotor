from decouple import config
from typing import List


class Settings:
    DATABASE_URL: str = config("DATABASE_URL")
    SECRET_KEY: str = config("SECRET_KEY", default="cambiar-en-produccion-ubermotor")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 12  # turno largo: 12 horas

    # CORS
    ALLOWED_HOSTS: List[str] = ["*"]

    # Tarifa mínima por carrera (soles) que el cliente le paga al conductor
    TARIFA_MINIMA_CARRERA: float = 3.0
    # Rechazos del conductor que disparan el descuento de saldo
    RECHAZOS_PARA_DESCUENTO: int = 3

    # Resend (recuperacion de contraseña por correo)
    RESEND_API_KEY: str = config("RESEND_API_KEY", default="")
    EMAIL_FROM_ADDRESS: str = config("EMAIL_FROM_ADDRESS", default="sistemas@jsinnovatech.com")
    EMAIL_FROM_NAME: str = config("EMAIL_FROM_NAME", default="UberMotor")


settings = Settings()
