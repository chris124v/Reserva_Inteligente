from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.config import settings
from app.dao.factory import DAOFactory

from app.services.search_service import (
    search_menus,
    search_menus_by_category,
    reindex_menus
)

#Este archivo nos sirve para definir los metodos de elastic search para buscar menus

router = APIRouter(prefix="/search", tags=["search"])


# DAO igual que en tus cuando lo hacemos normalmente en el route de menus
def get_menu_dao(db: Session = Depends(get_db)):
    return DAOFactory.get_menu_dao(settings.DATABASE_TYPE, db)


# Buscar por texto
@router.get("/menus")
def buscar_menus(q: str):
    return search_menus(q)


# Buscar por categoría
@router.get("/menus/category/{categoria}")
def buscar_menus_por_categoria(categoria: str):
    return search_menus_by_category(categoria)


# Reindexar
@router.post("/reindex")
def reindexar_menus(
    menu_dao=Depends(get_menu_dao)
):
    menus = menu_dao.get_all()
    return reindex_menus(menus)