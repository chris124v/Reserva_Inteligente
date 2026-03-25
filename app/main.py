from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.auth import router as auth_router
from app.config import settings

app = FastAPI(
    title="Reserva Inteligente de Restaurantes",
    description="API REST para gestión de reservas",
    version="1.0.0"
)

# CORS - Permite requests desde el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluye el router de auth
app.include_router(auth_router)

@app.get("/")
async def root():
    return {"message": "API funcionando"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)