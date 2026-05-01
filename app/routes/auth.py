from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database.session import get_db
from app.auth.cognito import CognitoClient, get_secret_hash
from app.config import settings
from app.models.user import RoleEnum, User
from app.dao.factory import DAOFactory

router = APIRouter(prefix="/auth", tags=["auth"])
cognito_client = CognitoClient()


def get_user_dao(db: Session = Depends(get_db)):
    return DAOFactory.get_user_dao(settings.DATABASE_TYPE, db)


class RegisterRequest(BaseModel):
    email: str
    password: str
    nombre: str
    rol: RoleEnum = RoleEnum.CLIENTE
    admin_code: str | None = None

class LoginRequest(BaseModel):
    email: str
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str
    email: str


@router.post("/register")
async def register(
    data: RegisterRequest,
    dao=Depends(get_user_dao)
):
    requested_role = data.rol or RoleEnum.CLIENTE

    if requested_role == RoleEnum.ADMIN:
        existing_local = dao.get_by_email(data.email)
        if existing_local and existing_local.rol != RoleEnum.ADMIN:
            raise HTTPException(
                status_code=403,
                detail="No se permite convertir un usuario existente en admin desde /register"
            )

        if settings.ADMIN_REGISTRATION_CODE:
            if not data.admin_code or data.admin_code != settings.ADMIN_REGISTRATION_CODE:
                raise HTTPException(status_code=403, detail="Código de admin inválido")
        else:
            # Bootstrap: solo permitir si no existe ningún admin aún
            if dao.get_first_admin():
                raise HTTPException(
                    status_code=403,
                    detail="No se permite registrar admins (configura ADMIN_REGISTRATION_CODE)"
                )
    else:
        requested_role = RoleEnum.CLIENTE

    result = cognito_client.register_user(
        email=data.email,
        password=data.password,
        nombre=data.nombre,
        rol=requested_role.value
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    local_user = dao.get_by_email(data.email)
    if not local_user:
        local_user = dao.create({
            "email": data.email,
            "nombre": data.nombre,
            "password_hash": "cognito",
            "rol": requested_role,
            "activo": True
        })

    if not local_user:
        raise HTTPException(
            status_code=500,
            detail="Usuario creado en Cognito pero no se pudo sincronizar en la BD local"
        )

    return result


@router.post("/login")
async def login(data: LoginRequest):
    result = cognito_client.authenticate_user(
        email=data.email,
        password=data.password
    )
    if not result["success"]:
        raise HTTPException(status_code=401, detail=result["error"])
    return result


@router.post("/refresh")
async def refresh_token(data: RefreshRequest):
    try:
        user_response = cognito_client.client.admin_get_user(
            UserPoolId=settings.COGNITO_USER_POOL_ID,
            Username=data.email
        )
        username = user_response['Username']

        secret_hash = get_secret_hash(
            username,
            settings.COGNITO_CLIENT_ID,
            settings.COGNITO_CLIENT_SECRET
        )

        response = cognito_client.client.admin_initiate_auth(
            UserPoolId=settings.COGNITO_USER_POOL_ID,
            ClientId=settings.COGNITO_CLIENT_ID,
            AuthFlow='REFRESH_TOKEN_AUTH',
            AuthParameters={
                'REFRESH_TOKEN': data.refresh_token,
                'SECRET_HASH': secret_hash
            }
        )

        tokens = response['AuthenticationResult']
        return {
            "access_token": tokens['AccessToken'],
            "id_token": tokens['IdToken'],
            "refresh_token": tokens.get('RefreshToken')
        }

    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))
