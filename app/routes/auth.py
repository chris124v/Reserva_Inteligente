from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database.session import get_db
from app.auth.cognito import CognitoClient
from app.config import settings
from app.auth.cognito import CognitoClient, get_secret_hash
from app.models.user import RoleEnum, User
from app.services.user_service import get_user_by_email

router = APIRouter(prefix="/auth", tags=["auth"])
cognito_client = CognitoClient()

#Modelos de pydantic para request y response
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


# Endpoints de autenticación
@router.post("/register")

# Registra un nuevo usuario en Cognito
async def register(data: RegisterRequest, db: Session = Depends(get_db)):

    requested_role = data.rol or RoleEnum.CLIENTE

    # Seguridad: no permitir auto-elevación a admin sin control.
    if requested_role == RoleEnum.ADMIN:
        # Si ya existe usuario local, no permitimos cambiar rol por "re-registro".
        existing_local = get_user_by_email(db, data.email)
        if existing_local and existing_local.rol != RoleEnum.ADMIN:
            raise HTTPException(
                status_code=403,
                detail="No se permite convertir un usuario existente en admin desde /register"
            )

        if settings.ADMIN_REGISTRATION_CODE:
            if not data.admin_code or data.admin_code != settings.ADMIN_REGISTRATION_CODE:
                raise HTTPException(
                    status_code=403,
                    detail="Código de admin inválido"
                )
        else:
            # Bootstrap: si no hay código configurado, solo se permite crear el primer admin
            # cuando aún no existe ningún admin en la BD.
            any_admin = db.query(User).filter(User.rol == RoleEnum.ADMIN).first()
            if any_admin:
                raise HTTPException(
                    status_code=403,
                    detail="No se permite registrar admins (configura ADMIN_REGISTRATION_CODE)"
                )
    else:
        requested_role = RoleEnum.CLIENTE

    # Aquí llamas a cognito_client.register_user()
    result = cognito_client.register_user(
        email=data.email,
        password=data.password,
        nombre=data.nombre,
        rol=requested_role.value
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    local_user = get_user_by_email(db, data.email)
    if not local_user:
        local_user = User(
            email=data.email,
            nombre=data.nombre,
            password_hash="cognito",
            rol=requested_role,
            activo=True,
        )
        db.add(local_user)
        db.commit()
        db.refresh(local_user)

    if not local_user:
        raise HTTPException(
            status_code=500,
            detail="Usuario creado en Cognito pero no se pudo sincronizar en la BD local"
        )

    return result

#Autentica un usuario y devuelve un JWT
@router.post("/login")

async def login(data: LoginRequest):
    
    result = cognito_client.authenticate_user(
        email=data.email,
        password=data.password
    )

    if not result["success"]:
        raise HTTPException(status_code=401, detail=result["error"])
    return result

#Refresca el token usando el usuario y el refresh token
@router.post("/refresh")
async def refresh_token(data: RefreshRequest):
    
    try:
        # Cognito requiere el sub/username para el SECRET_HASH en refresh
        # Primero obtenemos el username real desde Cognito

        user_response = cognito_client.client.admin_get_user(
            UserPoolId=settings.COGNITO_USER_POOL_ID,
            Username=data.email
        )

        # El Username en Cognito es el sub (UUID)
        username = user_response['Username']
        
        secret_hash = get_secret_hash(
            username,  # Cognito usa el username como identifier en esta parte
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
