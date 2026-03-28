from sqlalchemy.orm import Session
from app.models.user import User, RoleEnum
from app.schemas.user import UserCreate, UserUpdate

def get_user(db: Session, user_id: int):
    """Busca un usuario por su ID. Retorna None si no existe."""
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_email(db: Session, email: str):
    """
    Busca un usuario por su email.
    Se usa principalmente durante el login y registro
    para verificar si el usuario ya existe en la BD local.
    """
    return db.query(User).filter(User.email == email).first()

def get_all_users(db: Session):
    """
    Retorna la lista completa de usuarios.
    Solo debería ser accesible para administradores.
    """
    return db.query(User).all()

def create_user(db: Session, user: UserCreate):
    """
    Registra un nuevo usuario en la base de datos local.
    
    Importante: La contraseña real se maneja en AWS Cognito.
    Aquí solo guardamos un placeholder en password_hash
    porque el modelo lo requiere como not null, pero la
    autenticación real ocurre en Cognito.
    """
    # Verificamos que no exista ya un usuario con ese email
    existing = get_user_by_email(db, user.email)
    if existing:
        return None  # El route lanza el 400

    db_user = User(
        email=user.email,
        nombre=user.nombre,
        password_hash="cognito",  # La auth real está en Cognito
        rol=user.rol
        # activo queda en True por defecto (definido en el modelo)
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user(db: Session, user_id: int, user: UserUpdate):
    """
    Actualiza los datos de un usuario existente.
    Solo modifica los campos que vienen en el request.
    Retorna None si el usuario no existe.
    """
    db_user = get_user(db, user_id)
    if not db_user:
        return None

    # Solo actualizamos los campos enviados en el request
    update_data = user.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_user, field, value)

    db.commit()
    db.refresh(db_user)
    return db_user

def delete_user(db: Session, user_id: int):
    """
    Elimina un usuario del sistema.
    Por el CASCADE del modelo, también elimina sus
    reservas y pedidos asociados.
    Retorna None si el usuario no existe.
    """
    db_user = get_user(db, user_id)
    if not db_user:
        return None

    db.delete(db_user)
    db.commit()
    return db_user

def deactivate_user(db: Session, user_id: int):
    """
    Desactiva un usuario sin eliminarlo del sistema.
    Es una alternativa más segura al delete, ya que
    conserva el historial de reservas y pedidos.
    Retorna None si el usuario no existe.
    """
    db_user = get_user(db, user_id)
    if not db_user:
        return None

    db_user.activo = False
    db.commit()
    db.refresh(db_user)
    return db_user