from fastapi import APIRouter, Depends, HTTPException #Grupo de rutas, dao etc
from sqlalchemy.orm import Session #Sesion de sql alchemy
from pydantic import BaseModel #Modelos de validacion de datos
from app.database.session import get_db #Funcion que obtiene la sesion de la bd
from app.auth.cognito import CognitoClient, get_secret_hash #Cliente para comunicarse con cognito y generar el hash
from app.config import settings #Configuraciones del sistema
from app.models.user import RoleEnum, User #Modelo de usuario y enum de roles
from app.dao.factory import DAOFactory #Factory para usar el dao correcto

# Rutas de autenticación y registro usando AWS Cognito

router = APIRouter(prefix="/auth", tags=["auth"]) #Rutas agrupadas bajo /auth
cognito_client = CognitoClient() #Creacion del cliente de cognito

#Dependencia para obtener una sesion y luego el factory decide el dao que se va a usar
def get_user_dao(db: Session = Depends(get_db)):
    return DAOFactory.get_user_dao(settings.DATABASE_TYPE, db)

#Json de register
class RegisterRequest(BaseModel):
    email: str
    password: str
    nombre: str
    rol: RoleEnum = RoleEnum.CLIENTE
    admin_code: str | None = None

#Json para login
class LoginRequest(BaseModel):
    email: str
    password: str

#Json para refresh token
class RefreshRequest(BaseModel):
    refresh_token: str
    email: str

#Endpoint registrar un nuevo usuario
@router.post("/register")
async def register(
    data: RegisterRequest,
    dao=Depends(get_user_dao)
):
    requested_role = data.rol or RoleEnum.CLIENTE #Usa cliente por defecto

    #Esto seria para que un usuario existente no se convierta en admin de la nada
    if requested_role == RoleEnum.ADMIN:

        existing_local = dao.get_by_email(data.email)
        if existing_local and existing_local.rol != RoleEnum.ADMIN:
            raise HTTPException(
                status_code=403,
                detail="No se permite convertir un usuario existente en admin desde /register"
            )

        #Si es diferente del que obtenemos en el .env mandamos la excepcion
        if settings.ADMIN_REGISTRATION_CODE:
            if not data.admin_code or data.admin_code != settings.ADMIN_REGISTRATION_CODE:
                raise HTTPException(status_code=403, detail="Código de admin inválido")
        else:
            # Bootstrap: solo permitir si no existe ningún admin aún, es como para dar inicio al sistema
            if dao.get_first_admin():
                raise HTTPException(
                    status_code=403,
                    detail="No se permite registrar admins (configura ADMIN_REGISTRATION_CODE)"
                )
    else:
        requested_role = RoleEnum.CLIENTE #Si no es admin, forzamos a cliente 

    #Registramos el usuario en Cognito, si falla no seguimos con la BD local
    result = cognito_client.register_user(
        email=data.email,
        password=data.password,
        nombre=data.nombre,
        rol=requested_role.value
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    #Aqui sincronizamos todo con la bd local, primera busca si ya existe localmente lo que no deberia pasar
    local_user = dao.get_by_email(data.email)

    #Sino existe entonces lo creamos en la bd local
    if not local_user:
        local_user = dao.create({
            "email": data.email,
            "nombre": data.nombre,
            "password_hash": "cognito",
            "rol": requested_role,
            "activo": True
        })

    #En caso de algun error en la bd local
    if not local_user:
        raise HTTPException(
            status_code=500,
            detail="Usuario creado en Cognito pero no se pudo sincronizar en la BD local"
        )

    return result #Devuelve el resultado de cognito

#Ruta para hacer el login
@router.post("/login")
async def login(data: LoginRequest):

    #Result valida las credenciales con cognito 
    result = cognito_client.authenticate_user(
        email=data.email,
        password=data.password
    )

    #Sino es exitoso manda error de autenticacion
    if not result["success"]:
        raise HTTPException(status_code=401, detail=result["error"])
    return result

#Metodo para refresh token usando la que nos da el login, genera nuevos tokens
@router.post("/refresh")
async def refresh_token(data: RefreshRequest):


    try:

        #Busca el usuario en cognito
        user_response = cognito_client.client.admin_get_user(
            UserPoolId=settings.COGNITO_USER_POOL_ID,
            Username=data.email
        )
        username = user_response['Username'] #Obtiene el username real

        #Calcula el secret hash necesario para la autenticacion con refresh token
        secret_hash = get_secret_hash(
            username,
            settings.COGNITO_CLIENT_ID,
            settings.COGNITO_CLIENT_SECRET
        )

        #Incia el flujo de autenticacion con el refresh token auth que pide a cognito renovar tokens
        response = cognito_client.client.admin_initiate_auth(
            UserPoolId=settings.COGNITO_USER_POOL_ID,
            ClientId=settings.COGNITO_CLIENT_ID,
            AuthFlow='REFRESH_TOKEN_AUTH',
            AuthParameters={
                'REFRESH_TOKEN': data.refresh_token,
                'SECRET_HASH': secret_hash
            }
        )

        tokens = response['AuthenticationResult'] #Extrae los tokens nuevos
        
        #Retorna los tokens
        return {
            "access_token": tokens['AccessToken'],
            "id_token": tokens['IdToken'],
            "refresh_token": tokens.get('RefreshToken')
        }

    #Excepcion generica.
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))
