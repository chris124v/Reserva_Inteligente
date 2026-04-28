from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.menu import MenuCreate, MenuCreateRequest, MenuUpdate, MenuResponse
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
from app.auth.cognito import CognitoClient
from app.config import settings
from app.services.user_service import get_user_by_email, get_user
from app.models.user import RoleEnum
from app.services.restaurant_service import get_restaurant

router = APIRouter(prefix="/menus", tags=["menus"])

cognito_client = CognitoClient()


def _extract_email_from_cognito_user(user_response: dict) -> str | None:
    for attr in user_response.get("UserAttributes", []):
        if attr.get("Name") == "email":
            return attr.get("Value")
    return None


def _resolve_current_local_user_id(current_user: dict, db: Session) -> int | None:
    raw_user_id = current_user.get("usuario_id")
    if raw_user_id is not None:
        try:
            return int(raw_user_id)
        except (TypeError, ValueError):
            pass

    raw_numeric_id = current_user.get("sub") or current_user.get("username")
    if raw_numeric_id is not None:
        try:
            return int(raw_numeric_id)
        except (TypeError, ValueError):
            pass

    email = current_user.get("email")
    if email:
        local_user = get_user_by_email(db, email)
        if local_user:
            return local_user.id

    username = current_user.get("username") or current_user.get("sub")
    if not username:
        return None

    if "@" in username:
        local_user = get_user_by_email(db, username)
        return local_user.id if local_user else None

    try:
        user_response = cognito_client.client.admin_get_user(
            UserPoolId=settings.COGNITO_USER_POOL_ID,
            Username=username,
        )
        email = _extract_email_from_cognito_user(user_response)
        if not email:
            return None
        local_user = get_user_by_email(db, email)
        return local_user.id if local_user else None
    except Exception:
        return None


def _require_admin_local_user(payload: dict, db: Session):
    user_id = _resolve_current_local_user_id(payload, db)
    if not user_id:
        raise HTTPException(status_code=401, detail="Usuario no autenticado")

    local_user = get_user(db, user_id)
    if not local_user:
        raise HTTPException(status_code=401, detail="Usuario no autenticado o no sincronizado en BD local")

    if local_user.rol != RoleEnum.ADMIN:
        raise HTTPException(status_code=403, detail="Solo usuarios admin pueden modificar menús")

    return local_user

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
    menu: MenuCreateRequest,
    restaurante_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
    payload: dict = Depends(verify_jwt)  # Requiere autenticación
):
    """
    Crea un nuevo plato en el menú de un restaurante.
    Requiere estar autenticado.
    """
    local_user = _require_admin_local_user(payload, db)

    restaurante = get_restaurant(db, restaurante_id)
    if not restaurante:
        raise HTTPException(status_code=404, detail="Restaurante no encontrado")

    if restaurante.admin_id != local_user.id:
        raise HTTPException(status_code=403, detail="No tiene permiso para crear menús en este restaurante")

    nuevo_menu = create_menu(
        db,
        MenuCreate(**menu.model_dump(), restaurante_id=restaurante_id),
    )
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
    local_user = _require_admin_local_user(payload, db)

    menu_existente = get_menu(db, menu_id)
    if not menu_existente:
        raise HTTPException(status_code=404, detail="Menú no encontrado")

    restaurante = get_restaurant(db, menu_existente.restaurante_id)
    if not restaurante:
        raise HTTPException(status_code=404, detail="Restaurante no encontrado")

    if restaurante.admin_id != local_user.id:
        raise HTTPException(status_code=403, detail="No tiene permiso para actualizar este menú")

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
    local_user = _require_admin_local_user(payload, db)

    menu_existente = get_menu(db, menu_id)
    if not menu_existente:
        raise HTTPException(status_code=404, detail="Menú no encontrado")

    restaurante = get_restaurant(db, menu_existente.restaurante_id)
    if not restaurante:
        raise HTTPException(status_code=404, detail="Restaurante no encontrado")

    if restaurante.admin_id != local_user.id:
        raise HTTPException(status_code=403, detail="No tiene permiso para eliminar este menú")

    menu_eliminado = delete_menu(db, menu_id)
    if not menu_eliminado:
        raise HTTPException(status_code=404, detail="Menú no encontrado")
    return None