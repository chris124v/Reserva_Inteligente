from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.auth.cognito import CognitoClient
from app.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])
cognito_client = CognitoClient()

#Modelos de pydantic para request y response
class RegisterRequest(BaseModel):
    email: str
    password: str
    nombre: str
    
class LoginRequest(BaseModel):
    email: str
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str


# Endpoints de autenticación
@router.post("/register")

# Registra un nuevo usuario en Cognito
async def register(data: RegisterRequest):

    # Aquí llamas a cognito_client.register_user()
    result = cognito_client.register_user(
        email=data.email,
        password=data.password,
        nombre=data.nombre
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
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

#Refresca el token usando el refresh token
@router.post("/refresh")
async def refresh_token(data: RefreshRequest):
    
    try:
        response = cognito_client.client.admin_initiate_auth(
            UserPoolId=settings.COGNITO_USER_POOL_ID,
            ClientId=settings.COGNITO_CLIENT_ID,
            AuthFlow='REFRESH_TOKEN_AUTH',
            AuthParameters={
                'REFRESH_TOKEN': data.refresh_token
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
