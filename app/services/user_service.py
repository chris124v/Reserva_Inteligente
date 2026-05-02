from app.models.user import User, RoleEnum
from app.schemas.user import UserCreate
from app.auth.cognito import CognitoClient
from app.config import settings

_cognito_client = CognitoClient()


# Logica de negocio

def create_user(dao, user: UserCreate) -> User | None:
    """
    Registra un nuevo usuario en BD local.
    Retorna None si el email ya existe.
    """
    existing = dao.get_by_email(user.email)
    if existing:
        return None

    return dao.create({
        "email": user.email,
        "nombre": user.nombre,
        "password_hash": "cognito",
        "rol": user.rol,
        "activo": True
    })


def validate_update_permissions(
    current_local_user: User | None,
    target_user: User,
    master_admin_code: str | None,
) -> None:
    from fastapi import HTTPException

    is_owner = (
        current_local_user is not None and (
            current_local_user.id == target_user.id or
            current_local_user.email.lower() == target_user.email.lower()
        )
    )
    is_admin = current_local_user is not None and current_local_user.rol == RoleEnum.ADMIN

    if not is_owner and not is_admin:
        if current_local_user is None:
            raise HTTPException(status_code=401, detail="Usuario no autenticado o no sincronizado en BD local")
        raise HTTPException(status_code=403, detail="No tiene permiso para actualizar este usuario")

    if is_admin and not is_owner:
        if not settings.MASTER_ADMIN_CODE:
            raise HTTPException(status_code=403, detail="MASTER_ADMIN_CODE no configurado")
        if not master_admin_code or master_admin_code != settings.MASTER_ADMIN_CODE:
            raise HTTPException(status_code=403, detail="Código master admin inválido")


def validate_delete_permissions(
    current_local_user: User | None,
    target_user: User,
    master_admin_code: str | None,
) -> None:
    from fastapi import HTTPException

    is_owner = (
        current_local_user is not None and (
            current_local_user.id == target_user.id or
            current_local_user.email.lower() == target_user.email.lower()
        )
    )
    is_admin = current_local_user is not None and current_local_user.rol == RoleEnum.ADMIN

    if not is_owner and not is_admin:
        if current_local_user is None:
            raise HTTPException(status_code=401, detail="Usuario no autenticado o no sincronizado en BD local")
        raise HTTPException(status_code=403, detail="No tiene permiso para eliminar este usuario")

    if is_admin and not is_owner:
        if not settings.MASTER_ADMIN_CODE:
            raise HTTPException(status_code=403, detail="MASTER_ADMIN_CODE no configurado")
        if not master_admin_code or master_admin_code != settings.MASTER_ADMIN_CODE:
            raise HTTPException(status_code=403, detail="Código master admin inválido")


def sync_email_cognito(old_email: str, new_email: str) -> None:
    from fastapi import HTTPException
    try:
        _cognito_client.update_user_email(old_email, new_email)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"No se pudo actualizar el email en Cognito: {str(e)}")


# De JWT a usuario local 

def extract_email_from_cognito_user(user_response: dict) -> str | None:
    attrs = user_response.get("UserAttributes", [])
    for attr in attrs:
        if attr.get("Name") == "email":
            return attr.get("Value")
    return None


def resolve_cognito_username(current_user: dict) -> str | None:
    return current_user.get("username") or current_user.get("cognito:username")


def resolve_current_user_email(current_user: dict) -> str | None:
    email = current_user.get("email")
    if email:
        return email

    username = resolve_cognito_username(current_user)
    if not username:
        return None

    if "@" in username:
        return username

    try:
        user_response = _cognito_client.client.admin_get_user(
            UserPoolId=settings.COGNITO_USER_POOL_ID,
            Username=username,
        )
        return extract_email_from_cognito_user(user_response)
    except Exception:
        return None


def resolve_current_local_user_id(current_user: dict, dao) -> int | None:
    raw_user_id = current_user.get("usuario_id")
    if raw_user_id is not None:
        try:
            return int(raw_user_id)
        except (TypeError, ValueError):
            pass

    raw_numeric_id = current_user.get("sub")
    if raw_numeric_id is not None:
        try:
            return int(raw_numeric_id)
        except (TypeError, ValueError):
            pass

    email = resolve_current_user_email(current_user)
    if email:
        local_user = dao.get_by_email(email)
        if local_user:
            return local_user.id

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
            local_user = dao.get_by_email(email)
            if local_user:
                return local_user.id
    except Exception:
        local_user = dao.get_by_email(username)
        return local_user.id if local_user else None

    return None


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