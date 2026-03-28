from sqlalchemy.orm import Session
from app.models.restaurant import Restaurant
from app.schemas.restaurant import RestaurantCreate, RestaurantUpdate

def get_restaurant(db: Session, restaurant_id: int):
    """Busca un restaurante por su ID. Retorna None si no existe."""
    return db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()

def get_restaurant_by_email(db: Session, email: str):
    """
    Busca un restaurante por su email.
    Útil para evitar registrar el mismo restaurante dos veces.
    """
    return db.query(Restaurant).filter(Restaurant.email == email).first()

def get_all_restaurants(db: Session):
    """Retorna la lista completa de restaurantes registrados."""
    return db.query(Restaurant).all()

def get_restaurants_by_admin(db: Session, admin_id: int):
    """
    Retorna todos los restaurantes administrados por un usuario específico.
    Útil para que el admin vea solo sus propios restaurantes.
    """
    return db.query(Restaurant).filter(Restaurant.admin_id == admin_id).all()

def create_restaurant(db: Session, restaurant: RestaurantCreate, admin_id: int):
    """
    Registra un nuevo restaurante en el sistema.
    
    El admin_id viene del token JWT del usuario autenticado,
    no del body del request, por eso se pasa como parámetro separado.
    """
    # Verificamos que no exista ya un restaurante con ese email
    existing = get_restaurant_by_email(db, restaurant.email)
    if existing:
        return None  # El route se encarga de lanzar el 400

    db_restaurant = Restaurant(
        nombre=restaurant.nombre,
        descripcion=restaurant.descripcion,
        direccion=restaurant.direccion,
        telefono=restaurant.telefono,
        email=restaurant.email,
        hora_apertura=restaurant.hora_apertura,
        hora_cierre=restaurant.hora_cierre,
        total_mesas=restaurant.total_mesas,
        admin_id=admin_id  # Se asigna desde el token, no desde el request
    )
    db.add(db_restaurant)
    db.commit()
    db.refresh(db_restaurant)
    return db_restaurant

def update_restaurant(db: Session, restaurant_id: int, restaurant: RestaurantUpdate):
    """
    Actualiza los datos de un restaurante existente.
    Solo modifica los campos que vienen en el request (exclude_unset).
    Retorna None si el restaurante no existe.
    """
    db_restaurant = get_restaurant(db, restaurant_id)
    if not db_restaurant:
        return None

    # Solo actualizamos los campos que el usuario envió
    update_data = restaurant.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_restaurant, field, value)

    db.commit()
    db.refresh(db_restaurant)
    return db_restaurant

def delete_restaurant(db: Session, restaurant_id: int):
    """
    Elimina un restaurante del sistema.
    Por el CASCADE definido en el modelo, también elimina
    sus menús, reservas y pedidos asociados.
    Retorna None si el restaurante no existe.
    """
    db_restaurant = get_restaurant(db, restaurant_id)
    if not db_restaurant:
        return None

    db.delete(db_restaurant)
    db.commit()
    return db_restaurant