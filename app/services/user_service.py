from sqlalchemy.orm import Session
from app.models.user import User, RoleEnum
from app.schemas.user import UserCreate, UserUpdate
from app.auth.cognito import CognitoClient
from app.config import settings

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


# Funciones de resolucion (JWT -> Usuario Local)

_cognito_client = CognitoClient()


def extract_email_from_cognito_user(user_response: dict) -> str | None:
    """Extrae el email del response de admin_get_user de Cognito."""
    attrs = user_response.get("UserAttributes", [])
    for attr in attrs:
        if attr.get("Name") == "email":
            return attr.get("Value")
    return None


def resolve_cognito_username(current_user: dict) -> str | None:
    """
    Resuelve el username de Cognito desde el JWT.
    En access tokens suele venir como 'username'; en id tokens como 'cognito:username'.
    """
    return current_user.get("username") or current_user.get("cognito:username")


def resolve_current_user_email(current_user: dict) -> str | None:
    """
    Resuelve el email del usuario desde el JWT.
    
    Prioridad:
    1. Email directo en el token
    2. Username que contiene @ (es email)
    3. Consultar Cognito con username para obtener email
    """
    # Algunos tokens (id token) incluyen email directamente
    email = current_user.get("email")
    if email:
        return email

    username = resolve_cognito_username(current_user)
    if not username:
        return None

    # En algunos pools el username es el email
    if "@" in username:
        return username

    # Si username es UUID, consultamos Cognito para obtener email
    try:
        user_response = _cognito_client.client.admin_get_user(
            UserPoolId=settings.COGNITO_USER_POOL_ID,
            Username=username,
        )
        return extract_email_from_cognito_user(user_response)
    except Exception:
        return None


def resolve_current_local_user_id(current_user: dict, db: Session) -> int | None:
    """
    Resuelve el ID del usuario local (tabla users) a partir del JWT.

    Prioridad:
    1. usuario_id directo en el token
    2. sub numérico (compatibilidad)
    3. Email del token -> búsqueda en BD local
    4. Username del token -> Cognito -> email -> BD local
    """
    raw_user_id = current_user.get("usuario_id")
    if raw_user_id is not None:
        try:
            return int(raw_user_id)
        except (TypeError, ValueError):
            pass

    # Compatibilidad: si por alguna razón llega sub numérico
    raw_numeric_id = current_user.get("sub")
    if raw_numeric_id is not None:
        try:
            return int(raw_numeric_id)
        except (TypeError, ValueError):
            pass

    # Intentar con email
    email = resolve_current_user_email(current_user)
    if email:
        local_user = get_user_by_email(db, email)
        if local_user:
            return local_user.id

    # Fallback: intentar con username + Cognito
    username = resolve_cognito_username(current_user)
    if not username:
        return None

    try:
        user_response = _cognito_client.client.admin_get_user(
            UserPoolId=settings.COGNITO_USER_POOL_ID,
            Username=username,
        )
        email = extract_email_from_cognito_user(user_response)
        if email:
            local_user = get_user_by_email(db, email)
            if local_user:
                return local_user.id
    except Exception:
        # Si Cognito falla, intentar email como username (algunos flujos)
        local_user = get_user_by_email(db, username)
        return local_user.id if local_user else None

    return None


def resolve_current_local_user(current_user: dict, db: Session) -> User | None:
    """
    Resuelve el objeto User local desde el JWT.
    
    Intenta primero por ID, luego por email.
    Retorna None si no encuentra el usuario.
    """
    user_id = resolve_current_local_user_id(current_user, db)
    if user_id is not None:
        user = get_user(db, user_id)
        if user:
            return user

    email = resolve_current_user_email(current_user)
    if email:
        user = get_user_by_email(db, email)
        if user:
            return user

    return None