from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.emergencia import router as emergencia_router

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
def startup():
    #create_db()  # Alembic se encargará de la creación de las tablas
    print("RescueSync iniciado")

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