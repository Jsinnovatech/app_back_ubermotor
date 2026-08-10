from pydantic import BaseModel


class PaqueteOut(BaseModel):
    id: int
    nombre: str
    monto: int
    carreras: int

    class Config:
        from_attributes = True


class ComprarRecargaIn(BaseModel):
    paquete_id: int
    metodo: str = "yape"


class RecargaOut(BaseModel):
    id: int
    conductor_id: int
    paquete_id: int
    monto: int
    carreras: int
    metodo: str
    estado: str

    class Config:
        from_attributes = True
