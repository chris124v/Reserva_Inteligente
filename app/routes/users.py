from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.auth.middleware import verify_jwt
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
    user_id = current_user.get("sub") or current_user.get("usuario_id")
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Usuario no autenticado")
    
    db_user = get_user(db, user_id)
    
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
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
    
    # Validar permisos
    current_user_id = current_user.get("sub") or current_user.get("usuario_id")
    
    # El usuario solo puede actualizar su propio perfil, o es admin
    if db_user.id != current_user_id:
        # TODO: Validar que el usuario actual es admin
        raise HTTPException(
            status_code=403,
            detail="No tiene permiso para actualizar este usuario"
        )
    
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
    
    # Validar permisos
    current_user_id = current_user.get("sub") or current_user.get("usuario_id")
    
    if db_user.id != current_user_id:
        # TODO: Validar que el usuario actual es admin
        raise HTTPException(
            status_code=403,
            detail="No tiene permiso para eliminar este usuario"
        )
    
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
