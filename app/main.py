from fastapi import FastAPI

app = FastAPI(title="Reserva Inteligente de Restaurantes")

@app.get("/")
def read_root():
    return {"message": "API funcionando"}

@app.get("/health")
def health():
    return {"status": "ok"}