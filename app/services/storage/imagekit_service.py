# Subida de documentos del conductor (foto, DNI, licencia, antecedentes) a
# ImageKit. Mismo patron probado en Comanda/Casta de Gallos: SDK imagekitio==3.2.0
# (la ultima version del paquete tiene API distinta, no usarla).
import base64
import logging
from dataclasses import dataclass
from typing import Optional

from imagekitio import ImageKit
from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class UploadResult:
    url: str
    file_id: str
    thumbnail_url: Optional[str] = None


class ImageKitService:
    def __init__(self):
        try:
            self.client = ImageKit(
                private_key=settings.IMAGEKIT_PRIVATE_KEY,
                public_key=settings.IMAGEKIT_PUBLIC_KEY,
                url_endpoint=settings.IMAGEKIT_URL_ENDPOINT,
            )
            self._disponible = bool(settings.IMAGEKIT_PRIVATE_KEY)
        except Exception as e:
            logger.error(f"Error inicializando ImageKit: {e}")
            self.client = None
            self._disponible = False

    @property
    def disponible(self) -> bool:
        return self._disponible and self.client is not None

    def subir(self, file_content: bytes, file_name: str, folder: str) -> Optional[UploadResult]:
        if not self.disponible:
            logger.warning("ImageKit no configurado (faltan API keys) - no se sube el archivo")
            return None

        try:
            file_base64 = base64.b64encode(file_content).decode("utf-8")
            options = UploadFileRequestOptions(folder=folder, use_unique_file_name=True)
            resultado = self.client.upload_file(file=file_base64, file_name=file_name, options=options)

            if resultado and resultado.response_metadata.raw:
                data = resultado.response_metadata.raw
                return UploadResult(
                    url=data.get("url"),
                    file_id=data.get("file_id"),
                    thumbnail_url=data.get("thumbnail_url") or data.get("thumbnailUrl"),
                )
            return None
        except Exception as e:
            logger.error(f"Error subiendo a ImageKit: {e}")
            return None


imagekit_service = ImageKitService()
