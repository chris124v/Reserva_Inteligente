from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.auth.middleware import verify_jwt
from app.auth.cognito import CognitoClient
from app.config import settings
from app.schemas.restaurant import RestaurantCreate, RestaurantUpdate, RestaurantResponse
from app.services.user_service import (
    get_user_by_email,
    get_user,
    resolve_current_local_user_id,
)
from app.models.user import RoleEnum
from app.services.restaurant_service import (
    get_restaurant,
    get_restaurant_by_email,
    get_all_restaurants,
    create_restaurant,
    update_restaurant,
    delete_restaurant
)

router = APIRouter(prefix="/restaurants", tags=["restaurants"])
cognito_client = CognitoClient()


@router.post("/", response_model=RestaurantResponse, status_code=201)
async def crear_restaurante(
    restaurant_data: RestaurantCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(verify_jwt)
):
    """
    Crea un nuevo restaurante.
    El usuario autenticado se convierte en el administrador del restaurante.
    Solo los usuarios con rol ADMIN pueden crear restaurantes.
    """
    try:
        admin_id = resolve_current_local_user_id(current_user, db)
        
        if not admin_id:
            raise HTTPException(status_code=401, detail="Usuario no autenticado")

        admin_user = get_user(db, admin_id)
        if not admin_user:
            raise HTTPException(status_code=401, detail="Usuario no autenticado o no sincronizado en BD local")

        if admin_user.rol != RoleEnum.ADMIN:
            raise HTTPException(status_code=403, detail="Solo usuarios admin pueden crear restaurantes")
        
        # Verificar que el email no exista
        existing = get_restaurant_by_email(db, restaurant_data.email)
        if existing:
            raise HTTPException(
                status_code=400,
                detail="Ya existe un restaurante registrado con ese email"
            )
        
        # Crear el restaurante
        db_restaurant = create_restaurant(
            db=db,
            restaurant=restaurant_data,
            admin_id=admin_id
        )
        
        return db_restaurant
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al crear el restaurante: {str(e)}")


@router.get("/", response_model=list[RestaurantResponse])
async def listar_restaurantes(
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=100),
    skip: int = Query(0, ge=0)
):
    """
    Obtiene la lista de todos los restaurantes registrados.
    No requiere autenticación.
    """
    restaurants = get_all_restaurants(db)
    
    # Aplicar paginación
    return restaurants[skip : skip + limit]


@router.put("/{restaurant_id}", response_model=RestaurantResponse)
async def actualizar_restaurante(
    restaurant_id: int,
    restaurant_update: RestaurantUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(verify_jwt)
):
    """
    Actualiza los datos de un restaurante.
    Solo el administrador del restaurante puede actualizarlo.
    
    Todos los campos son opcionales. Solo se actualizan los que se envíen.
    """
    db_restaurant = get_restaurant(db, restaurant_id)
    
    if not db_restaurant:
        raise HTTPException(status_code=404, detail="Restaurante no encontrado")
    
    # Validar permisos: usuario debe ser admin del restaurante
    admin_id = resolve_current_local_user_id(current_user, db)

    if not admin_id:
        raise HTTPException(status_code=401, detail="Usuario no autenticado")

    admin_user = get_user(db, admin_id)
    if not admin_user:
        raise HTTPException(status_code=401, detail="Usuario no autenticado o no sincronizado en BD local")

    if admin_user.rol != RoleEnum.ADMIN:
        raise HTTPException(status_code=403, detail="Solo usuarios admin pueden actualizar restaurantes")
    
    if db_restaurant.admin_id != admin_id:
        raise HTTPException(
            status_code=403,
            detail="No tiene permiso para actualizar este restaurante"
        )
    
    # Si se intenta actualizar el email, verificar que sea único
    if restaurant_update.email and restaurant_update.email != db_restaurant.email:
        existing = get_restaurant_by_email(db, restaurant_update.email)
        if existing:
            raise HTTPException(
                status_code=400,
                detail="Ya existe un restaurante con ese email"
            )
    
    # Actualizar
    updated_restaurant = update_restaurant(db, restaurant_id, restaurant_update)
    
    return updated_restaurant


@router.delete("/{restaurant_id}", status_code=204)
async def eliminar_restaurante(
    restaurant_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(verify_jwt)
):
    """
    Elimina un restaurante del sistema.
    Solo el administrador del restaurante puede eliminarlo.
    
    Esto eliminará también todos los menús, reservas y pedidos
    asociados al restaurante.
    """
    db_restaurant = get_restaurant(db, restaurant_id)
    
    if not db_restaurant:
        raise HTTPException(status_code=404, detail="Restaurante no encontrado")
    
    # Validar permisos
    admin_id = resolve_current_local_user_id(current_user, db)

    if not admin_id:
        raise HTTPException(status_code=401, detail="Usuario no autenticado")

    admin_user = get_user(db, admin_id)
    if not admin_user:
        raise HTTPException(status_code=401, detail="Usuario no autenticado o no sincronizado en BD local")

    if admin_user.rol != RoleEnum.ADMIN:
        raise HTTPException(status_code=403, detail="Solo usuarios admin pueden eliminar restaurantes")
    
    if db_restaurant.admin_id != admin_id:
        raise HTTPException(
            status_code=403,
            detail="No tiene permiso para eliminar este restaurante"
        )
    
    # Eliminar
    delete_restaurant(db, restaurant_id)
    
    return None
