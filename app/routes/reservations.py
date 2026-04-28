from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.auth.middleware import verify_jwt
from app.auth.cognito import CognitoClient
from app.config import settings
from app.services.user_service import get_user_by_email
from app.services.user_service import get_user
from app.models.user import RoleEnum
from app.schemas.reservation import (
    ReservationCreate,
    ReservationUpdate,
    ReservationResponse
)
from app.services.reservation_service import (
    get_reservation,
    get_reservations_by_usuario,
    get_reservations_by_restaurante,
    create_reservation,
    cancel_reservation
)
from app.services.restaurant_service import get_restaurant

router = APIRouter(prefix="/reservations", tags=["reservations"])
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


@router.post("/", response_model=ReservationResponse, status_code=201)
async def crear_reserva(
    reservation_data: ReservationCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(verify_jwt)
):
    """
    Crea una nueva reserva para el usuario autenticado.
    
    - **restaurante_id**: ID del restaurante
    - **fecha**: Fecha de la reserva (YYYY-MM-DD), debe ser futura
    - **hora**: Hora de la reserva (HH:MM)
    - **cantidad_personas**: Número de personas (1-20)
    - **notas**: Notas adicionales (opcional)
    """
    try:
        usuario_id = _resolve_current_local_user_id(current_user, db)
        
        if not usuario_id:
            raise HTTPException(status_code=401, detail="Usuario no autenticado")

        local_user = get_user(db, usuario_id)
        if not local_user:
            raise HTTPException(status_code=401, detail="Usuario no autenticado o no sincronizado en BD local")

        if local_user.rol != RoleEnum.CLIENTE:
            raise HTTPException(status_code=403, detail="Solo usuarios cliente pueden crear reservas")
        
        restaurante = get_restaurant(db, reservation_data.restaurante_id)
        if not restaurante:
            raise HTTPException(status_code=404, detail="Restaurante no encontrado")

        total_mesas = restaurante.total_mesas
        
        # Crear la reserva
        db_reservation = create_reservation(
            db=db,
            reservation=reservation_data,
            usuario_id=usuario_id,
            total_mesas=total_mesas
        )
        
        if not db_reservation:
            raise HTTPException(
                status_code=400,
                detail="Para ese dia ya esta lleno"
            )
        
        return db_reservation
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al crear la reserva: {str(e)}")


@router.get("/", response_model=list[ReservationResponse])
async def listar_mis_reservas(
    db: Session = Depends(get_db),
    current_user: dict = Depends(verify_jwt),
    limit: int = Query(10, ge=1, le=100),
    skip: int = Query(0, ge=0)
):
    """
    Obtiene todas las reservas del usuario autenticado.
    
    - **limit**: Número máximo de registros (default: 10, máximo: 100)
    - **skip**: Número de registros a saltar para paginación
    """
    usuario_id = _resolve_current_local_user_id(current_user, db)
    
    if not usuario_id:
        raise HTTPException(status_code=401, detail="Usuario no autenticado")

    local_user = get_user(db, usuario_id)
    if not local_user:
        raise HTTPException(status_code=401, detail="Usuario no autenticado o no sincronizado en BD local")

    if local_user.rol != RoleEnum.CLIENTE:
        raise HTTPException(status_code=403, detail="Lo siento, solo clientes tienen reservas")
    
    reservations = get_reservations_by_usuario(db, usuario_id)
    
    # Aplicar paginación
    return reservations[skip : skip + limit]


@router.put("/{reservation_id}", response_model=ReservationResponse)
async def actualizar_reserva(
    reservation_id: int,
    reservation_update: ReservationUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(verify_jwt)
):
    """
    Actualiza una reserva (estado, mesa, notas).
    Solo admin del restaurante puede cambiar estado y mesa.
    El usuario puede actualizar solo sus notas.
    """
    db_reservation = get_reservation(db, reservation_id)
    
    if not db_reservation:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    
    usuario_id = _resolve_current_local_user_id(current_user, db)

    if not usuario_id:
        raise HTTPException(status_code=401, detail="Usuario no autenticado")
    
    # Si no es admin, solo puede actualizar notas
    if db_reservation.usuario_id != usuario_id:
        if reservation_update.estado or reservation_update.numero_mesa:
            raise HTTPException(
                status_code=403,
                detail="Solo el admin puede cambiar estado y mesa"
            )
    
    # Actualizar campos
    update_data = reservation_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_reservation, field, value)
    
    db.commit()
    db.refresh(db_reservation)
    return db_reservation


@router.delete("/{reservation_id}", status_code=204)
async def cancelar_reserva(
    reservation_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(verify_jwt)
):
    """
    Cancela una reserva.
    Solo reservas en estado RESERVADA pueden ser canceladas.
    """
    db_reservation = get_reservation(db, reservation_id)
    
    if not db_reservation:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    
    usuario_id = _resolve_current_local_user_id(current_user, db)

    if not usuario_id:
        raise HTTPException(status_code=401, detail="Usuario no autenticado")
    
    if db_reservation.usuario_id != usuario_id:
        raise HTTPException(status_code=403, detail="No tiene permiso para cancelar esta reserva")
    
    # Validar estado
    if db_reservation.estado.value != "reservada":
        raise HTTPException(
            status_code=400,
            detail=f"No se puede cancelar una reserva en estado {db_reservation.estado.value}"
        )
    
    # Cancelar
    cancel_reservation(db, reservation_id)
    
    return None


@router.get("/restaurante/{restaurante_id}", response_model=list[ReservationResponse])
async def listar_reservas_restaurante(
    restaurante_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(verify_jwt),
    limit: int = Query(10, ge=1, le=100),
    skip: int = Query(0, ge=0)
):
    """
    Obtiene todas las reservas de un restaurante.
    Solo el dueño del restaurante puede ver esta información.
    
    - **restaurante_id**: ID del restaurante
    - **limit**: Número máximo de registros
    - **skip**: Número de registros a saltar
    """
    usuario_id = _resolve_current_local_user_id(current_user, db)
    if not usuario_id:
        raise HTTPException(status_code=401, detail="Usuario no autenticado")

    local_user = get_user(db, usuario_id)
    if not local_user:
        raise HTTPException(status_code=401, detail="Usuario no autenticado o no sincronizado en BD local")

    if local_user.rol != RoleEnum.ADMIN:
        raise HTTPException(status_code=403, detail="Solo admins pueden ver reservas por restaurante")

    restaurante = get_restaurant(db, restaurante_id)
    if not restaurante:
        raise HTTPException(status_code=404, detail="Restaurante no encontrado")

    if restaurante.admin_id != local_user.id:
        raise HTTPException(status_code=403, detail="No tiene permiso para ver las reservas de este restaurante")
    
    reservations = get_reservations_by_restaurante(db, restaurante_id)
    
    # Aplicar paginación
    return reservations[skip : skip + limit]


