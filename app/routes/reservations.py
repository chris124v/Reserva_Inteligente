from fastapi import APIRouter, HTTPException, Depends, Query
from datetime import date, time
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.auth.middleware import verify_jwt
from app.schemas.reservation import (
    ReservationCreate,
    ReservationUpdate,
    ReservationCancel,
    ReservationResponse
)
from app.services.reservation_service import (
    get_reservation,
    get_reservations_by_usuario,
    get_reservations_by_restaurante,
    check_disponibilidad,
    create_reservation,
    cancel_reservation,
    confirm_reservation
)

router = APIRouter(prefix="/reservations", tags=["reservations"])


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
        usuario_id = current_user.get("sub") or current_user.get("usuario_id")
        
        if not usuario_id:
            raise HTTPException(status_code=401, detail="Usuario no autenticado")
        
        # TODO: Validar que el restaurante existe y obtener número total de mesas
        total_mesas = 10  # Por defecto, esto debería venir del restaurante
        
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
                detail="No hay mesas disponibles para esa fecha y hora"
            )
        
        return db_reservation
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al crear la reserva: {str(e)}")


@router.get("/{reservation_id}", response_model=ReservationResponse)
async def obtener_reserva(
    reservation_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(verify_jwt)
):
    """
    Obtiene los detalles de una reserva específica.
    Solo el usuario propietario o admin del restaurante pueden verla.
    """
    db_reservation = get_reservation(db, reservation_id)
    
    if not db_reservation:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    
    usuario_id = current_user.get("sub") or current_user.get("usuario_id")
    
    # TODO: Validar si es dueño del restaurante
    if db_reservation.usuario_id != usuario_id:
        raise HTTPException(status_code=403, detail="No tiene permiso para ver esta reserva")
    
    return db_reservation


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
    usuario_id = current_user.get("sub") or current_user.get("usuario_id")
    
    if not usuario_id:
        raise HTTPException(status_code=401, detail="Usuario no autenticado")
    
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
    
    usuario_id = current_user.get("sub") or current_user.get("usuario_id")
    
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
    Solo reservas en estado PENDIENTE o CONFIRMADA pueden ser canceladas.
    """
    db_reservation = get_reservation(db, reservation_id)
    
    if not db_reservation:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    
    usuario_id = current_user.get("sub") or current_user.get("usuario_id")
    
    if db_reservation.usuario_id != usuario_id:
        raise HTTPException(status_code=403, detail="No tiene permiso para cancelar esta reserva")
    
    # Validar estado
    if db_reservation.estado.value not in ["pendiente", "confirmada"]:
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
    # TODO: Validar que el usuario es dueño del restaurante
    
    reservations = get_reservations_by_restaurante(db, restaurante_id)
    
    # Aplicar paginación
    return reservations[skip : skip + limit]


@router.post("/{reservation_id}/confirm", response_model=ReservationResponse)
async def confirmar_reserva(
    reservation_id: int,
    numero_mesa: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(verify_jwt)
):
    """
    Confirma una reserva y asigna un número de mesa.
    Solo el admin del restaurante puede hacer esto.
    """
    db_reservation = get_reservation(db, reservation_id)
    
    if not db_reservation:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    
    # TODO: Validar que el usuario es admin del restaurante
    
    if db_reservation.estado.value != "pendiente":
        raise HTTPException(
            status_code=400,
            detail="Solo se pueden confirmar reservas pendientes"
        )
    
    if numero_mesa <= 0:
        raise HTTPException(status_code=400, detail="Número de mesa inválido")
    
    # Confirmar
    confirm_reservation(db, reservation_id, numero_mesa)
    
    updated = get_reservation(db, reservation_id)
    return updated
