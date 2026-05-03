from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes.auth import router as auth_router
from .routes.users import router as users_router
from .routes.restaurants import router as restaurants_router
from .routes.menus import router as menus_router
from .routes.reservations import router as reservations_router
from .routes.orders import router as orders_router
from .config import settings

app = FastAPI(
    title="Reserva Inteligente de Restaurantes",
    description="API REST para gestión de reservas",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(restaurants_router)
app.include_router(menus_router)
app.include_router(reservations_router)
app.include_router(orders_router)

@app.get("/")
async def root():
    return {"message": "API funcionando"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)