from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.exceptions import CustomException
from app.api.v1.auth import router as auth_router
from app.api.v1.conductores import router as conductores_router
from app.api.v1.clientes import router as clientes_router
from app.api.v1.viajes import router as viajes_router
from app.api.v1.recargas import router as recargas_router
from app.api.v1.admin import router as admin_router

app = FastAPI(title="UberMotor API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# (router, prefix, tags) — tags=None cuando el router ya define los suyos
ROUTERS = [
    (auth_router, "", None),
    (conductores_router, "/api/v1", None),
    (clientes_router, "/api/v1", None),
    (viajes_router, "/api/v1", None),
    (recargas_router, "/api/v1", None),
    (admin_router, "/api/v1", None),
]

for router, prefix, tags in ROUTERS:
    if tags:
        app.include_router(router, prefix=prefix, tags=tags)
    else:
        app.include_router(router, prefix=prefix)

print(f"✅ {len(ROUTERS)} routers montados exitosamente")


@app.exception_handler(CustomException)
async def custom_exception_handler(request, exc: CustomException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": True, "message": exc.message, "error_code": exc.error_code},
    )


@app.get("/")
async def health_check():
    return {"status": "ok", "service": "ubermotor-api"}
