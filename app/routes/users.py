from fastapi import APIRouter, HTTPException, Depends, Query, Header
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.auth.middleware import verify_jwt
from app.auth.cognito import CognitoClient
from app.config import settings
from app.models.user import RoleEnum, User
from app.schemas.user import UserUpdate, UserResponse
from app.services.user_service import (
    get_user,
    get_user_by_email,
    get_all_users,
    update_user,
    deactivate_user,
    resolve_current_local_user,
    resolve_current_local_user_id,
    resolve_current_user_email,
)

router = APIRouter(prefix="/users", tags=["users"])
cognito_client = CognitoClient()


@router.get("/", response_model=list[UserResponse])
async def listar_usuarios(
    db: Session = Depends(get_db),
    current_user: dict = Depends(verify_jwt),
    limit: int = Query(10, ge=1, le=100),
    skip: int = Query(0, ge=0)
):
    """
    Obtiene la lista de todos los usuarios.
    Requiere autenticación.
    
    - limit: Número máximo de registros (default: 10, máximo: 100)
    - skip: Número de registros a saltar para paginación
    """
    users = get_all_users(db)
    
    # Aplicar paginación
    return users[skip : skip + limit]

@router.get("/me", response_model=UserResponse)
async def obtener_mi_perfil(
    db: Session = Depends(get_db),
    current_user: dict = Depends(verify_jwt)
):
    """
    Obtiene el perfil del usuario autenticado.
    Requiere token JWT válido.
    """
    db_user = resolve_current_local_user(current_user, db)

    if not db_user:
        raise HTTPException(
            status_code=401,
            detail="Usuario no autenticado o no sincronizado en BD local"
        )
    
    return db_user


@router.put("/{user_id}", response_model=UserResponse)
async def actualizar_usuario(
    user_id: int,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(verify_jwt),
    master_admin_code: str | None = Header(None, alias="X-Master-Admin-Code"),
):
    """
    Actualiza los datos de un usuario.
    
    Un usuario puede actualizar su propio perfil.
    Los admins solo pueden actualizar otros perfiles si presentan el código master.
    """
    db_user = get_user(db, user_id)
    
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Validar permisos (owner o admin)
    current_local_user = resolve_current_local_user(current_user, db)
    current_user_id = current_local_user.id if current_local_user else None
    current_user_email = (
        current_local_user.email
        if current_local_user is not None
        else resolve_current_user_email(current_user)
    )
    is_admin = current_local_user is not None and current_local_user.rol == RoleEnum.ADMIN

    is_owner_by_id = current_user_id is not None and db_user.id == current_user_id
    is_owner_by_email = current_user_email is not None and db_user.email.lower() == current_user_email.lower()
    is_owner = is_owner_by_id or is_owner_by_email

    # Fallback: si no podemos resolver usuario local (p. ej. email cambio y el token quedó viejo),
    # verificamos identidad con el `sub` del access token contra Cognito.
    if not is_owner and current_local_user is None:
        token_sub = current_user.get("sub")
        if token_sub and db_user.email:
            try:
                cognito_sub = cognito_client.get_user_sub_by_email(db_user.email)
                if str(cognito_sub) == str(token_sub):
                    is_owner = True
            except Exception:
                # Si Cognito no está disponible o falla, mantenemos la decisión original.
                pass

    # Cualquier usuario autenticado puede actualizar su propio perfil.
    # Para actualizar a otra persona, debe ser admin y presentar master code.
    if not is_owner and not is_admin:
        if current_user_id is None and current_user_email is None:
            raise HTTPException(
                status_code=401,
                detail="Usuario no autenticado o no sincronizado en BD local",
            )
        raise HTTPException(status_code=403, detail="No tiene permiso para actualizar este usuario")

    # Admin: para actualizar a otro usuario requiere código master.
    if is_admin and not is_owner:
        if not settings.MASTER_ADMIN_CODE:
            raise HTTPException(status_code=403, detail="MASTER_ADMIN_CODE no configurado")
        if not master_admin_code or master_admin_code != settings.MASTER_ADMIN_CODE:
            raise HTTPException(status_code=403, detail="Código master admin inválido")

    # Solo master puede modificar el estado 'activo' (si realmente cambia).
    if user_update.activo is not None and user_update.activo != db_user.activo:
        if not is_admin:
            raise HTTPException(status_code=403, detail="No tiene permiso para modificar el estado del usuario")
        if not settings.MASTER_ADMIN_CODE:
            raise HTTPException(status_code=403, detail="MASTER_ADMIN_CODE no configurado")
        if not master_admin_code or master_admin_code != settings.MASTER_ADMIN_CODE:
            raise HTTPException(status_code=403, detail="Código master admin inválido")
    
    # Si se intenta actualizar el email, verificar que sea único y sincronizar en Cognito.
    if user_update.email and user_update.email != db_user.email:
        existing = get_user_by_email(db, user_update.email)
        if existing:
            raise HTTPException(status_code=400, detail="Ya existe un usuario con ese email")

        old_email = db_user.email
        new_email = user_update.email
        try:
            cognito_client.update_user_email(old_email, new_email)
        except Exception as e:
            raise HTTPException(
                status_code=502,
                detail=f"No se pudo actualizar el email en Cognito: {str(e)}",
            )
    
    # Actualizar
    updated_user = update_user(db, user_id, user_update)
    
    return updated_user


@router.delete("/{user_id}", status_code=204)
async def eliminar_usuario(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(verify_jwt),
    master_admin_code: str | None = Header(None, alias="X-Master-Admin-Code"),
):
    """
    Desactiva/elimina un usuario del sistema.
    
    Un usuario puede eliminar su propia cuenta.
    Los admins solo pueden eliminar otras cuentas si presentan el código master.
    
    Se desactiva el usuario
    """
    db_user = get_user(db, user_id)
    
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Validar permisos (dueno o admin)
    current_local_user = resolve_current_local_user(current_user, db)
    current_user_id = current_local_user.id if current_local_user else None
    current_user_email = current_local_user.email if current_local_user else resolve_current_user_email(current_user)
    is_admin = current_local_user is not None and current_local_user.rol == RoleEnum.ADMIN

    is_owner_by_id = current_user_id is not None and db_user.id == current_user_id
    is_owner_by_email = (
        current_user_email is not None
        and db_user.email.lower() == current_user_email.lower()
    )

    if not (is_owner_by_id or is_owner_by_email or is_admin):
        if current_user_id is None and current_user_email is None:
            raise HTTPException(
                status_code=401,
                detail="Usuario no autenticado o no sincronizado en BD local"
            )
    
        # TODO: Validar que el usuario actual es admin
        raise HTTPException(status_code=403, detail="No tiene permiso para eliminar este usuario")

    is_owner = is_owner_by_id or is_owner_by_email

    # Admin: para desactivar a otro usuario requiere código master.
    if is_admin and not is_owner:
        if not settings.MASTER_ADMIN_CODE:
            raise HTTPException(status_code=403, detail="MASTER_ADMIN_CODE no configurado")
        if not master_admin_code or master_admin_code != settings.MASTER_ADMIN_CODE:
            raise HTTPException(status_code=403, detail="Código master admin inválido")
    
    deactivated = deactivate_user(db, db_user.id)
    if not deactivated:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    return None
