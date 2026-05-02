from app.models.user import User, RoleEnum
from app.schemas.user import UserCreate
from app.auth.cognito import CognitoClient
from app.config import settings

_cognito_client = CognitoClient() #Llamamos a la instacnia global de cognito


# Logica de negocio

def create_user(dao, user: UserCreate) -> User | None:
    """
    Registra un nuevo usuario en bd escogida.
    Retorna None si el email ya existe. Tambien validamos con los schemas
    """
    # Aqui llamamos al dao de la BD que sea para revisar si ya existe o no
    existing = dao.get_by_email(user.email)
    if existing:
        return None

    # usamos las clases dao para crear el usuario, no el modelo directamente
    return dao.create({
        "email": user.email,
        "nombre": user.nombre,
        "password_hash": "cognito",
        "rol": user.rol,
        "activo": True
    })

#Funcion para validar si el usuario actual tiene permisos para actualizar otro usuario
def validate_update_permissions(
    current_local_user: User | None, #Usuario ya autenticado
    target_user: User,              #Usuario que se quiere actualizar
    master_admin_code: str | None, #Codigo master
) -> None:
    from fastapi import HTTPException

    #Determina si el usuario actual es dueno la cuenta, si lo es la puede modificar sin permisos adiciones
    is_owner = (
        current_local_user is not None and (
            current_local_user.id == target_user.id or
            current_local_user.email.lower() == target_user.email.lower()
        )
    )

    #Determina si el usuario esta registrado como admin, si lo es puede modificar cualquier cuenta pero necesita el master code
    is_admin = current_local_user is not None and current_local_user.rol == RoleEnum.ADMIN

    #Excepciones si no es ningununo de los dos
    if not is_owner and not is_admin:
        if current_local_user is None:
            raise HTTPException(status_code=401, detail="Usuario no autenticado o no sincronizado en BD local")
        raise HTTPException(status_code=403, detail="No tiene permiso para actualizar este usuario")

    #Excepcion si si es admin pero no owner o no tiene el master code
    if is_admin and not is_owner:
        if not settings.MASTER_ADMIN_CODE:
            raise HTTPException(status_code=403, detail="MASTER_ADMIN_CODE no configurado")
        if not master_admin_code or master_admin_code != settings.MASTER_ADMIN_CODE:
            raise HTTPException(status_code=403, detail="Código master admin inválido")

#Lo mismo pero para poder eliminar un usuario
def validate_delete_permissions(
    current_local_user: User | None,
    target_user: User,
    master_admin_code: str | None,
) -> None:
    from fastapi import HTTPException

    #Verificamos que sea dueno o si es admin 
    is_owner = (
        current_local_user is not None and (
            current_local_user.id == target_user.id or
            current_local_user.email.lower() == target_user.email.lower()
        )
    )
    is_admin = current_local_user is not None and current_local_user.rol == RoleEnum.ADMIN

    #Si no es ninguno de los dos, no puede eliminar
    if not is_owner and not is_admin:
        if current_local_user is None:
            raise HTTPException(status_code=401, detail="Usuario no autenticado o no sincronizado en BD local")
        raise HTTPException(status_code=403, detail="No tiene permiso para eliminar este usuario")

    #Si es admin pero no owner, necesita el master code para eliminar
    if is_admin and not is_owner:
        if not settings.MASTER_ADMIN_CODE:
            raise HTTPException(status_code=403, detail="MASTER_ADMIN_CODE no configurado")
        if not master_admin_code or master_admin_code != settings.MASTER_ADMIN_CODE:
            raise HTTPException(status_code=403, detail="Código master admin inválido")

#Metodo para sincronizar el email en cognito, se llama cuando un usuario cambia su email en la BD local
def sync_email_cognito(old_email: str, new_email: str) -> None:
    from fastapi import HTTPException
    try:
        _cognito_client.update_user_email(old_email, new_email)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"No se pudo actualizar el email en Cognito: {str(e)}")


# De JWT a usuario local 

# Obtiene el atributo de email de cognito para devolverlo 
def extract_email_from_cognito_user(user_response: dict) -> str | None:
    attrs = user_response.get("UserAttributes", [])
    for attr in attrs:
        if attr.get("Name") == "email":
            return attr.get("Value")
    return None

# Resueleve el useraname de la persona en el jwt osea lo obtien directament desde el jwt
def resolve_cognito_username(current_user: dict) -> str | None:
    return current_user.get("username") or current_user.get("cognito:username")

# Intenta obtener el email del usuario que fue autenticado ya previamente
def resolve_current_user_email(current_user: dict) -> str | None:
    
    #Si ya jwt lo da entonces lo devuelve
    email = current_user.get("email")
    if email:
        return email

    username = resolve_cognito_username(current_user)
    if not username:
        return None

    if "@" in username:
        return username
    
    #Si el username no es un email, intentamos obtener el email de cognito usando el username
    try:
        user_response = _cognito_client.client.admin_get_user(
            UserPoolId=settings.COGNITO_USER_POOL_ID,
            Username=username,
        )
        return extract_email_from_cognito_user(user_response) #extrae el email de la respuesta de cognito
    except Exception:
        return None

#Devuelve el usuario local que corresponde al usuario autenticado en cognito
def resolve_current_local_user_id(current_user: dict, dao) -> int | None:
    raw_user_id = current_user.get("usuario_id") #Si jwt ya lo trae lo convierte a int
    
    if raw_user_id is not None:
        try:
            return int(raw_user_id)
        except (TypeError, ValueError):
            pass
    
    #Lo utilizamos como fallback
    raw_numeric_id = current_user.get("sub")
    if raw_numeric_id is not None:
        try:
            return int(raw_numeric_id)
        except (TypeError, ValueError):
            pass
    
    #Si obtiene el email busca ese usuario en la bd local
    email = resolve_current_user_email(current_user)
    if email:
        local_user = dao.get_by_email(email)
        if local_user:
            return local_user.id

    username = resolve_cognito_username(current_user)
    if not username:
        return None

    #Si el username no es un email, intentamos obtener el email de cognito usando el username y luego buscar ese email en la bd local para obtener su id
    try:
        user_response = _cognito_client.client.admin_get_user(
            UserPoolId=settings.COGNITO_USER_POOL_ID,
            Username=username,
        )
        email = extract_email_from_cognito_user(user_response)
        if email:
            local_user = dao.get_by_email(email)
            if local_user:
                return local_user.id
    except Exception:
        local_user = dao.get_by_email(username)
        return local_user.id if local_user else None

    return None

# Metodo principal para dar con el usuario local a partir del jwt, se llama en los endpoints que necesitan autenticacion para obtener el usuario local completo y asi obtenemos el get me
def resolve_current_local_user(current_user: dict, dao) -> User | None:
    user_id = resolve_current_local_user_id(current_user, dao)
    if user_id is not None:
        user = dao.get_by_id(user_id)
        if user:
            return user

    email = resolve_current_user_email(current_user)
    if email:
        return dao.get_by_email(email)

    return None