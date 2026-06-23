from fastapi import APIRouter, HTTPException, Query
from app.services.routes_service import calcular_rutas

# Ruta para el modulo de rutas de entrega optimizadas
router = APIRouter(prefix="/routes", tags=["routes"])

@router.get("/delivery")
async def obtener_rutas_entrega(
    repartidores: int = Query(2, ge=1, le=10, description="Numero de repartidores disponibles")
):
    """
    Calcula las rutas de entrega optimizadas para pedidos a domicilio.

    Usa el algoritmo de vecino mas cercano para determinar el orden optimo
    en que cada repartidor debe realizar sus entregas, minimizando la
    distancia total recorrida.

    - **repartidores**: cantidad de repartidores disponibles (default: 2, max: 10)
    """
    try:
        resultado = calcular_rutas(num_repartidores=repartidores)
        return resultado
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Error al conectar con Neo4J o calcular rutas: {str(e)}"
        )
