from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.auth.middleware import verify_jwt
from app.config import settings
from app.models.user import RoleEnum
from app.schemas.reservation import ReservationCreate, ReservationUpdate, ReservationResponse
from app.dao.factory import DAOFactory
from app.services.user_service import resolve_current_local_user_id
from app.services.reservation_service import (
    create_reservation,
    validate_reservation_owner,
    validate_reservation_cancelable,
)

#Ruta para reservas en el sistema
router = APIRouter(prefix="/reservations", tags=["reservations"])

#Metodos paara obtener los daos necesarios
def get_reservation_dao(db: Session = Depends(get_db)):
    return DAOFactory.get_reservation_dao(settings.DATABASE_TYPE, db)

def get_user_dao(db: Session = Depends(get_db)):
    return DAOFactory.get_user_dao(settings.DATABASE_TYPE, db)

def get_restaurant_dao(db: Session = Depends(get_db)):
    return DAOFactory.get_restaurant_dao(settings.DATABASE_TYPE, db)

#Resolver user en caso de que no este autenticado o no este y ay
def _resolve_user(current_user, user_dao):
    
    from fastapi import HTTPException
    usuario_id = resolve_current_local_user_id(current_user, user_dao)
    if not usuario_id:
        raise HTTPException(status_code=401, detail="Usuario no autenticado")
    local_user = user_dao.get_by_id(usuario_id)
    if not local_user:
        raise HTTPException(status_code=401, detail="Usuario no autenticado o no sincronizado en BD local")
    return local_user

#Metodo para crear una reservam validamos que el usuario sea cliente, que la cree en un restaurante que existe y que el local no este lleno ese dia
@router.post("/", response_model=ReservationResponse, status_code=201)
async def crear_reserva(
    reservation_data: ReservationCreate,
    current_user: dict = Depends(verify_jwt),
    reservation_dao=Depends(get_reservation_dao),
    user_dao=Depends(get_user_dao),
    restaurant_dao=Depends(get_restaurant_dao)
):
    local_user = _resolve_user(current_user, user_dao)

    if local_user.rol != RoleEnum.CLIENTE:
        raise HTTPException(status_code=403, detail="Solo usuarios cliente pueden crear reservas")

    restaurante = restaurant_dao.get_by_id(reservation_data.restaurante_id)
    if not restaurante:
        raise HTTPException(status_code=404, detail="Restaurante no encontrado")

    db_reservation = create_reservation(reservation_dao, reservation_data, local_user.id, restaurante.total_mesas)
    if not db_reservation:
        raise HTTPException(status_code=400, detail="Para ese día ya está lleno")

    return db_reservation

#Ruta para listar las reservas del usuario autenticado que claramente debe ser cliente
@router.get("/", response_model=list[ReservationResponse])
async def listar_mis_reservas(
    current_user: dict = Depends(verify_jwt),
    limit: int = Query(10, ge=1, le=100),
    skip: int = Query(0, ge=0),
    reservation_dao=Depends(get_reservation_dao),
    user_dao=Depends(get_user_dao)
):
    local_user = _resolve_user(current_user, user_dao)

    if local_user.rol != RoleEnum.CLIENTE:
        raise HTTPException(status_code=403, detail="Solo clientes tienen reservas")

    reservations = reservation_dao.get_by_usuario(local_user.id)
    return reservations[skip: skip + limit]

#Ruta para actualuzar una reserva, obteniendo el numero de reserva y verificando que no se cambien estados si es el dueno
@router.put("/{reservation_id}", response_model=ReservationResponse)
async def actualizar_reserva(
    reservation_id: int,
    reservation_update: ReservationUpdate,
    current_user: dict = Depends(verify_jwt),
    reservation_dao=Depends(get_reservation_dao),
    user_dao=Depends(get_user_dao)
):
    db_reservation = reservation_dao.get_by_id(reservation_id)
    if not db_reservation:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")

    local_user = _resolve_user(current_user, user_dao)

    if db_reservation.usuario_id != local_user.id:
        if reservation_update.estado or reservation_update.numero_mesa:
            raise HTTPException(status_code=403, detail="Solo el admin puede cambiar estado y mesa")

    update_data = reservation_update.model_dump(exclude_unset=True)
    return reservation_dao.update(db_reservation, update_data)

#Ruta de cancelar, reserva, si es el dueno de la reserva puede hacerlo sino no
@router.delete("/{reservation_id}", status_code=204)
async def cancelar_reserva(
    reservation_id: int,
    current_user: dict = Depends(verify_jwt),
    reservation_dao=Depends(get_reservation_dao),
    user_dao=Depends(get_user_dao)
):
    db_reservation = reservation_dao.get_by_id(reservation_id)
    if not db_reservation:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")

    local_user = _resolve_user(current_user, user_dao)
    validate_reservation_owner(db_reservation, local_user.id)
    validate_reservation_cancelable(db_reservation)

    reservation_dao.cancel(db_reservation)
    return None

#Esta ruta es para el admin del restaurante por ende se valida que sea admin y autenticado
@router.get("/restaurante/{restaurante_id}", response_model=list[ReservationResponse])
async def listar_reservas_restaurante(
    restaurante_id: int,
    current_user: dict = Depends(verify_jwt),
    limit: int = Query(10, ge=1, le=100),
    skip: int = Query(0, ge=0),
    reservation_dao=Depends(get_reservation_dao),
    user_dao=Depends(get_user_dao),
    restaurant_dao=Depends(get_restaurant_dao)
):
    local_user = _resolve_user(current_user, user_dao)

    if local_user.rol != RoleEnum.ADMIN:
        raise HTTPException(status_code=403, detail="Solo admins pueden ver reservas por restaurante")

    restaurante = restaurant_dao.get_by_id(restaurante_id)
    if not restaurante:
        raise HTTPException(status_code=404, detail="Restaurante no encontrado")

    if restaurante.admin_id != local_user.id:
        raise HTTPException(status_code=403, detail="No tiene permiso para ver las reservas de este restaurante")

    reservations = reservation_dao.get_by_restaurante(restaurante_id)
    return reservations[skip: skip + limit]

