from fastapi import APIRouter
from typing import List
from app.services.search_service import (
    search_menus,
    search_menus_by_category,
    reindex_menus
)
import os
import httpx

router = APIRouter(prefix="/search", tags=["search"])

API_SERVICE_URL = os.getenv("API_SERVICE_URL", "http://api-service:80")


@router.get("/menus", response_model=List[dict])
def buscar_menus(q: str):
    return search_menus(q)


@router.get("/menus/category/{categoria}", response_model=List[dict])
def buscar_menus_por_categoria(categoria: str):
    return search_menus_by_category(categoria)


@router.post("/reindex")
def reindexar_menus():
    # Obtiene menus desde la API principal y llama a la función que reindexa
    url = f"{API_SERVICE_URL}/menus"
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(url)
            resp.raise_for_status()
            menus = resp.json()
    except Exception as e:
        return {"error": str(e)}

    return reindex_menus(menus)
