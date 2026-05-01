from fastapi import APIRouter, HTTPException, Depends, Query, Header
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.auth.middleware import verify_jwt
from app.config import settings
from app.models.user import RoleEnum
from app.schemas.user import UserUpdate, UserResponse
from app.dao.factory import DAOFactory
from app.services.user_service import (
    create_user,
    validate_update_permissions,
    validate_delete_permissions,
    sync_email_cognito,
    resolve_current_local_user,
)

router = APIRouter(prefix="/users", tags=["users"])


def get_user_dao(db: Session = Depends(get_db)):
    return DAOFactory.get_user_dao(settings.DATABASE_TYPE, db)


@router.get("/", response_model=list[UserResponse])
async def listar_usuarios(
    current_user: dict = Depends(verify_jwt),
    limit: int = Query(10, ge=1, le=100),
    skip: int = Query(0, ge=0),
    dao=Depends(get_user_dao)
):
    users = dao.get_all()
    return users[skip: skip + limit]


@router.get("/me", response_model=UserResponse)
async def obtener_mi_perfil(
    current_user: dict = Depends(verify_jwt),
    dao=Depends(get_user_dao)
):
    db_user = resolve_current_local_user(current_user, dao)
    if not db_user:
        raise HTTPException(status_code=401, detail="Usuario no autenticado o no sincronizado en BD local")
    return db_user


@router.put("/{user_id}", response_model=UserResponse)
async def actualizar_usuario(
    user_id: int,
    user_update: UserUpdate,
    current_user: dict = Depends(verify_jwt),
    master_admin_code: str | None = Header(None, alias="X-Master-Admin-Code"),
    dao=Depends(get_user_dao)
):
    target_user = dao.get_by_id(user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    current_local_user = resolve_current_local_user(current_user, dao)
    validate_update_permissions(current_local_user, target_user, master_admin_code)

    if user_update.activo is not None and user_update.activo != target_user.activo:
        if current_local_user is None or current_local_user.rol != RoleEnum.ADMIN:
            raise HTTPException(status_code=403, detail="No tiene permiso para modificar el estado del usuario")
        if not master_admin_code or master_admin_code != settings.MASTER_ADMIN_CODE:
            raise HTTPException(status_code=403, detail="Código master admin inválido")

    if user_update.email and user_update.email != target_user.email:
        existing = dao.get_by_email(user_update.email)
        if existing:
            raise HTTPException(status_code=400, detail="Ya existe un usuario con ese email")
        sync_email_cognito(target_user.email, user_update.email)

    update_data = user_update.model_dump(exclude_unset=True)
    return dao.update(target_user, update_data)


@router.delete("/{user_id}", status_code=204)
async def eliminar_usuario(
    user_id: int,
    current_user: dict = Depends(verify_jwt),
    master_admin_code: str | None = Header(None, alias="X-Master-Admin-Code"),
    dao=Depends(get_user_dao)
):
    target_user = dao.get_by_id(user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    current_local_user = resolve_current_local_user(current_user, dao)
    validate_delete_permissions(current_local_user, target_user, master_admin_code)

    dao.deactivate(target_user)
    return None