from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.auth.middleware import verify_jwt
from app.auth.cognito import CognitoClient
from app.config import settings
from app.models.user import RoleEnum, User
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.services.user_service import (
    get_user,
    get_user_by_email,
    get_all_users,
    create_user,
    update_user,
    delete_user,
    deactivate_user
)

router = APIRouter(prefix="/users", tags=["users"])
cognito_client = CognitoClient()


def _extract_email_from_cognito_user(user_response: dict) -> str | None:
    attrs = user_response.get("UserAttributes", [])
    for attr in attrs:
        if attr.get("Name") == "email":
            return attr.get("Value")
    return None


def _resolve_current_user_email(current_user: dict) -> str | None:
    # Algunos tokens (id token) incluyen email directamente
    email = current_user.get("email")
    if email:
        return email

    username = current_user.get("username") or current_user.get("sub")
    if not username:
        return None

    # En algunos pools el username es el email
    if "@" in username:
        return username

    # Si username/sub es UUID, consultamos Cognito para obtener email
    try:
        user_response = cognito_client.client.admin_get_user(
            UserPoolId=settings.COGNITO_USER_POOL_ID,
            Username=username,
        )
        return _extract_email_from_cognito_user(user_response)
    except Exception:
        return None


def _resolve_current_local_user_id(current_user: dict, db: Session) -> int | None:
    """
    Resuelve el ID del usuario local (tabla users) a partir del JWT.

    Prioriza `usuario_id` cuando existe y, para tokens de Cognito,
    usa `username/sub` -> admin_get_user -> email -> usuario local.
    """
    raw_user_id = current_user.get("usuario_id")
    if raw_user_id is not None:
        try:
            return int(raw_user_id)
        except (TypeError, ValueError):
            pass

    # Compatibilidad: si por alguna razon llega sub/username numerico
    raw_numeric_id = current_user.get("sub") or current_user.get("username")
    if raw_numeric_id is not None:
        try:
            return int(raw_numeric_id)
        except (TypeError, ValueError):
            pass

    email = _resolve_current_user_email(current_user)
    if email:
        local_user = get_user_by_email(db, email)
        if local_user:
            return local_user.id

    username = current_user.get("username") or current_user.get("sub")
    if not username:
        return None

    try:
        user_response = cognito_client.client.admin_get_user(
            UserPoolId=settings.COGNITO_USER_POOL_ID,
            Username=username,
        )
    except Exception:
        # Fallback: algunos flujos usan el email como username en Cognito
        local_user = get_user_by_email(db, username)
        return local_user.id if local_user else None

    email = _extract_email_from_cognito_user(user_response)
    if not email:
        return None

    local_user = get_user_by_email(db, email)
    return local_user.id if local_user else None


def _resolve_current_local_user(current_user: dict, db: Session) -> User | None:
    user_id = _resolve_current_local_user_id(current_user, db)
    if user_id is not None:
        user = get_user(db, user_id)
        if user:
            return user

    email = _resolve_current_user_email(current_user)
    if email:
        return get_user_by_email(db, email)

    return None


@router.post("/", response_model=UserResponse, status_code=201)
async def crear_usuario(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Crea un nuevo usuario en la base de datos local.
    
    Se usa después del registro en Cognito para sincronizar el usuario en la BD.
    
    - **email**: Email único del usuario
    - **nombre**: Nombre completo del usuario
    - **password**: Contraseña (se valida en Cognito, no se almacena aquí)
    - **rol**: CLIENTE o ADMIN (default: CLIENTE)
    """
    try:
        # Verificar que el email no exista
        existing = get_user_by_email(db, user_data.email)
        if existing:
            raise HTTPException(
                status_code=400,
                detail="Ya existe un usuario registrado con ese email"
            )
        
        # Crear el usuario
        db_user = create_user(db, user_data)
        
        return db_user
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al crear el usuario: {str(e)}")


@router.get("/me", response_model=UserResponse)
async def obtener_mi_perfil(
    db: Session = Depends(get_db),
    current_user: dict = Depends(verify_jwt)
):
    """
    Obtiene el perfil del usuario autenticado.
    Requiere token JWT válido.
    """
    user_id = _resolve_current_local_user_id(current_user, db)
    
    db_user = None

    if user_id:
        db_user = get_user(db, user_id)

    if not db_user:
        current_email = _resolve_current_user_email(current_user)
        if current_email:
            db_user = get_user_by_email(db, current_email)

    if not db_user:
        raise HTTPException(
            status_code=401,
            detail="Usuario no autenticado o no sincronizado en BD local"
        )
    
    return db_user


@router.get("/", response_model=list[UserResponse])
async def listar_usuarios(
    db: Session = Depends(get_db),
    current_user: dict = Depends(verify_jwt),
    limit: int = Query(10, ge=1, le=100),
    skip: int = Query(0, ge=0)
):
    """
    Obtiene la lista de todos los usuarios.
    Solo los administradores pueden acceder.
    
    - **limit**: Número máximo de registros (default: 10, máximo: 100)
    - **skip**: Número de registros a saltar para paginación
    """
    # TODO: Validar que el usuario es admin
    # Por ahora cualquier usuario autenticado puede ver la lista
    
    users = get_all_users(db)
    
    # Aplicar paginación
    return users[skip : skip + limit]


@router.get("/{user_id}", response_model=UserResponse)
async def obtener_usuario(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtiene los datos públicos de un usuario específico.
    No requiere autenticación (pero podría restricción según necesidades).
    """
    db_user = get_user(db, user_id)
    
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Validación: si el usuario no está activo, solo admin o el mismo usuario pueden verlo
    # TODO: Implementar lógica más granular de permisos
    
    return db_user


@router.put("/{user_id}", response_model=UserResponse)
async def actualizar_usuario(
    user_id: int,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(verify_jwt)
):
    """
    Actualiza los datos de un usuario.
    
    Un usuario puede actualizar su propio perfil.
    Los admins pueden actualizar cualquier perfil.
    
    Campos actualizables:
    - **nombre**: Nombre del usuario
    - **email**: Email (debe ser único)
    - **activo**: Estado del usuario (solo admin)
    """
    db_user = get_user(db, user_id)
    
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Validar permisos (dueno o admin)
    current_local_user = _resolve_current_local_user(current_user, db)
    current_user_id = current_local_user.id if current_local_user else None
    current_user_email = current_local_user.email if current_local_user else _resolve_current_user_email(current_user)
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
    
    # El usuario solo puede actualizar su propio perfil, o es admin
        # TODO: Validar que el usuario actual es admin
        raise HTTPException(status_code=403, detail="No tiene permiso para actualizar este usuario")
    
    # Si se intenta actualizar el email, verificar que sea único
    if user_update.email and user_update.email != db_user.email:
        existing = get_user_by_email(db, user_update.email)
        if existing:
            raise HTTPException(
                status_code=400,
                detail="Ya existe un usuario con ese email"
            )
    
    # Actualizar
    updated_user = update_user(db, user_id, user_update)
    
    return updated_user


@router.delete("/{user_id}", status_code=204)
async def eliminar_usuario(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(verify_jwt)
):
    """
    Desactiva/elimina un usuario del sistema.
    
    Un usuario puede eliminar su propia cuenta.
    Los admins pueden eliminar cualquier cuenta.
    
    NOTA: Esto desactiva el usuario, no lo elimina físicamente,
    para conservar el historial de reservas y pedidos.
    """
    db_user = get_user(db, user_id)
    
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Validar permisos (dueno o admin)
    current_local_user = _resolve_current_local_user(current_user, db)
    current_user_id = current_local_user.id if current_local_user else None
    current_user_email = current_local_user.email if current_local_user else _resolve_current_user_email(current_user)
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
    
    # Deactivar usuario
    deactivate_user(db, user_id)
    
    return None


@router.put("/{user_id}/activate", response_model=UserResponse)
async def reactivar_usuario(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(verify_jwt)
):
    """
    Reactiva un usuario desactivado.
    Solo los admins pueden reactivar usuarios.
    """
    db_user = get_user(db, user_id)
    
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # TODO: Validar que el usuario actual es admin
    
    if db_user.activo:
        raise HTTPException(
            status_code=400,
            detail="Este usuario ya está activo"
        )
    
    # Reactivar
    db_user.activo = True
    db.commit()
    db.refresh(db_user)
    
    return db_user
