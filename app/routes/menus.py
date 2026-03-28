from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.menu import MenuCreate, MenuUpdate, MenuResponse
from app.services.menu_service import (
    get_menu,
    get_all_menus,
    get_menus_by_restaurante,
    create_menu,
    update_menu,
    delete_menu
)
from app.auth.middleware import verify_jwt
from typing import List

router = APIRouter(prefix="/menus", tags=["menus"])

@router.get("/", response_model=List[MenuResponse])
async def listar_menus(
    restaurante_id: int = None,
    db: Session = Depends(get_db)
):
    """
    Lista todos los menús. Si se pasa restaurante_id como query param,
    filtra los menús de ese restaurante específico.
    Ejemplo: GET /menus?restaurante_id=1
    """
    if restaurante_id:
        return get_menus_by_restaurante(db, restaurante_id)
    return get_all_menus(db)


@router.get("/restaurante/{restaurante_id}", response_model=List[MenuResponse])
async def listar_menus_restaurante(
    restaurante_id: int,
    db: Session = Depends(get_db)
):
    """Lista los menús de un restaurante por ID (ruta esperada por los tests)."""
    return get_menus_by_restaurante(db, restaurante_id)

@router.get("/{menu_id}", response_model=MenuResponse)
async def obtener_menu(
    menu_id: int,
    db: Session = Depends(get_db)
):
    """Obtiene el detalle de un menú específico por su ID."""
    menu = get_menu(db, menu_id)
    if not menu:
        raise HTTPException(status_code=404, detail="Menú no encontrado")
    return menu

@router.post("/", response_model=MenuResponse, status_code=201)
async def crear_menu(
    menu: MenuCreate,
    db: Session = Depends(get_db),
    payload: dict = Depends(verify_jwt)  # Requiere autenticación
):
    """
    Crea un nuevo plato en el menú de un restaurante.
    Requiere estar autenticado.
    """
    nuevo_menu = create_menu(db, menu)
    if not nuevo_menu:
        raise HTTPException(status_code=400, detail="Error al crear el menú")
    return nuevo_menu

@router.put("/{menu_id}", response_model=MenuResponse)
async def actualizar_menu(
    menu_id: int,
    menu: MenuUpdate,
    db: Session = Depends(get_db),
    payload: dict = Depends(verify_jwt)  # Requiere autenticación
):
    """
    Actualiza los datos de un plato existente.
    Solo se modifican los campos enviados en el request.
    """
    menu_actualizado = update_menu(db, menu_id, menu)
    if not menu_actualizado:
        raise HTTPException(status_code=404, detail="Menú no encontrado")
    return menu_actualizado

@router.delete("/{menu_id}", status_code=204)
async def eliminar_menu(
    menu_id: int,
    db: Session = Depends(get_db),
    payload: dict = Depends(verify_jwt)  # Requiere autenticación
):
    """
    Elimina un plato del menú.
    Requiere estar autenticado.
    """
    menu_eliminado = delete_menu(db, menu_id)
    if not menu_eliminado:
        raise HTTPException(status_code=404, detail="Menú no encontrado")
    return None