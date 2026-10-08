from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from clients.redis_client import close_redis, init_redis
from routers.emergencia import router as emergencia_router
from routers.auth import router as auth_router
from routers.lote import router as lotes_router
from routers.oferta import router as oferta_router
API_PREFIX = "/api/rescue"

app = FastAPI(
    title="RescueSync Backend API",
    version="1.0.0",
    description="Backend principal de RescueSync"
)

# para resolver el problema de CORS en local
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    #create_db()  # Alembic se encargará de la creación de las tablas
    app.state.redis = await init_redis()
    print("RescueSync iniciado")


@app.on_event("shutdown")
async def shutdown():
    await close_redis(app.state.redis)

@app.get("/health", tags=["Health"])
def health():
    return {
    "status": "ok",
    "service": "rescuesync-backend",
}

app.include_router(
    emergencia_router,
    prefix=API_PREFIX
)
app.include_router(auth_router, prefix=API_PREFIX)

app.include_router(
    lotes_router,
    prefix=API_PREFIX
)

app.include_router(
    oferta_router,
    prefix=API_PREFIX
)