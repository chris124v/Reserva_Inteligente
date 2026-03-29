"""
Tests esenciales para el módulo de autenticacion con AWS Cognito. 
"""
 
import pytest
from unittest.mock import MagicMock, patch
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from fastapi.security import HTTPAuthorizationCredentials
 
# Fixtures

# Preparan directamente el entorno de pruebas, son mocks de configuraciones reales
 
@pytest.fixture(autouse=True) #Define que es un fixture que se corre en cada test
def mock_settings(): 
    with patch("app.auth.cognito.settings") as m: # Reemplaza las variables por estos valoers fake:
        m.AWS_REGION = "us-east-2"
        m.COGNITO_USER_POOL_ID = "us-east-2_72geNIkP2"
        m.COGNITO_CLIENT_ID = "fake-client-id"
        m.COGNITO_CLIENT_SECRET = "fake-client-secret"
        yield m #Devuelme el mock para que sea usado en los tests
 
# Prepare el cliente de cognito mockeado para no hacer llamadas reales a AWS
@pytest.fixture
def cognito(mock_settings):
    with patch("boto3.client"): #Con patch desactivamos la creacion real del cliente osea retorna el mock
        from app.auth.cognito import CognitoClient 
        c = CognitoClient() #importa y cre la clase dentro de patch
        c.client = MagicMock() #Magic mock simula cualquier objeto, osea el cliente
        return c #Cliente listo
 
# Fixture de la API
@pytest.fixture
def api():
    with patch("app.auth.cognito.settings") as m: #Nuevamente todo desde el patch
        m.AWS_REGION = "us-east-2"
        m.COGNITO_USER_POOL_ID = "us-east-2_72geNIkP2"
        m.COGNITO_CLIENT_ID = "fake-client-id"
        m.COGNITO_CLIENT_SECRET = "fake-client-secret"
        with patch("boto3.client"):
            from app.routes.auth import router #Importa autenticacion de rutas
            app = FastAPI() 
            app.include_router(router) #Incluye las rutas de autenticacion en la app
            return TestClient(app) #TestClient de FastAPI para hacer peticiones a la API sin levantar un servidor real
 
 

# get_secret_hash

# Genera un hash de seguridad que cognito espera para algunas operaciones
 
def test_secret_hash_es_deterministico(): #Mismo resultado si son los mismos inputs
    from app.auth.cognito import get_secret_hash 
    assert get_secret_hash("a", "b", "c") == get_secret_hash("a", "b", "c") #Si es deterministico, el mismo input da el mismo output

# Verifica que el hash cambia si el usuario cambia, si es el mismo hash problema
def test_secret_hash_diferente_por_usuario():
    from app.auth.cognito import get_secret_hash
    assert get_secret_hash("user1", "b", "c") != get_secret_hash("user2", "b", "c")
 
 
# register_user
 
 # Recibe el fixture de cognito y configura el mock
def test_register_exitoso(cognito):
    cognito.client.admin_create_user.return_value = {}
    cognito.client.admin_set_user_password.return_value = {}
    cognito.client.admin_update_user_attributes.return_value = {}
    
    # Llama a la función de registro con datos de prueba ESTO ES REAL
    result = cognito.register_user("new@test.com", "Pass123!", "Test")
    assert result["success"] is True #Verifica que el resultado indique éxito

# Esto es solo en caso de que el usuario ya exista, el mock simula la excepción que boto3 lanzaría
def test_register_falla_si_usuario_existe(cognito):
    cognito.client.admin_create_user.side_effect = Exception("User already exists")
 
    result = cognito.register_user("exist@test.com", "Pass123!", "Test")
    assert result["success"] is False
    assert "error" in result
 
 
# authenticate_user

#Recibe otra vez a cognito preparado para simular la autenticacion
def test_login_exitoso(cognito):

    #Configuramos el mock
    cognito.client.admin_initiate_auth.return_value = {
        "AuthenticationResult": {
            "AccessToken": "access-token",
            "IdToken": "id-token",
            "RefreshToken": "refresh-token"
        }
    }
 
    #Llamamos a la funcion de autenticacion con datos de prueba
    result = cognito.authenticate_user("user@test.com", "Pass123!")
    assert result["success"] is True
    assert result["access_token"] == "access-token" #Verificacion de resultado

# Simula el caso de contraseña incorrecta, boto3 lanzaria una excepcion que simula el mock
def test_login_password_incorrecta(cognito):

    #Creamos excepciones personalizadas para simular las que boto3 lanzaría
    cognito.client.exceptions.NotAuthorizedException = type("NotAuthorizedException", (Exception,), {})
    cognito.client.exceptions.UserNotConfirmedException = type("UserNotConfirmedException", (Exception,), {})
    cognito.client.admin_initiate_auth.side_effect = cognito.client.exceptions.NotAuthorizedException("bad pass")
    
    #Llamamos a la funcion de autenticacion con contraseña incorrecta
    result = cognito.authenticate_user("user@test.com", "wrong")
    assert result["success"] is False
 
 
# verify_token

def test_verify_token_valido(cognito):

    # Simula una llave valida desde JWKS y un payload de access token valido.
    with patch.object(cognito.jwks_client, "get_signing_key_from_jwt", return_value=MagicMock(key="fake-key")), \
         patch("app.auth.cognito.jwt.decode", return_value={"sub": "123", "token_use": "access", "client_id": "fake-client-id"}):
        result = cognito.verify_token("valid.token")
    assert result["success"] is True

# Funcion que simula el caso de token expirado, boto3 lanzaria una excepcion que simula el mock
def test_verify_token_expirado(cognito):
    import jwt as pyjwt #Importamos jwt para usar la excepcion de token expirado que boto3 lanzaria, el mock simula esa excepcion cuando se intenta decodificar el token, lo que hace que la verificacion del token falle y retorne un error indicando que el token ha expirado
    with patch.object(cognito.jwks_client, "get_signing_key_from_jwt", return_value=MagicMock(key="fake-key")), \
         patch("app.auth.cognito.jwt.decode", side_effect=pyjwt.ExpiredSignatureError()): #Lanza una excepcion directamente
        result = cognito.verify_token("expired.token")
    assert result["success"] is False
    assert "expirado" in result["error"]
 
 
# Middleware
 
@pytest.mark.asyncio #Permite utilizar funciones asincronas en los tests, necesario para probar el middleware que es async
async def test_middleware_sin_token():
    from app.auth.middleware import verify_jwt #Importamos la funcion a testear
    with pytest.raises(HTTPException) as exc: #Esperamos que se lance una excepcion HTTPException porque no se proporciona un token
        await verify_jwt(None)
    assert exc.value.status_code == 401 #Verificamos que el código de estado de la excepción sea 401, lo que indica que no se proporcionó un token

#Probar directamente un token valido. 
@pytest.mark.asyncio
async def test_middleware_token_valido():

    # Creamos credenciales HTTP Bearer simuladas (nuevo contrato del middleware).
    from app.auth.middleware import verify_jwt
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid.token")

    #Mockeamos la función de verificación de token para que retorne un payload simulado indicando que el token es válido, lo que hace que el middleware devuelva la información del usuario en lugar de lanzar una excepción
    with patch("app.auth.middleware.cognito_client") as mock:
        mock.verify_token.return_value = {"success": True, "payload": {"sub": "123"}}
        result = await verify_jwt(creds)
    assert result["sub"] == "123"
 
 
# Endpoints

#Prueban toda la cadena de request - funcion y response

#Usamos el fixture de la API
def test_endpoint_register(api):

    #Usa el mock de register user
    with patch("app.routes.auth.cognito_client") as mock:
        mock.register_user.return_value = {"success": True, "message": "Registrado"}

        #Simula una petición POST al endpoint de registro con datos de prueba, lo que hace que se llame a la función de registro mockeada y se verifique que el endpoint responde con éxito
        r = api.post("/auth/register", json={"email": "a@b.com", "password": "Pass1!", "nombre": "A"})
    assert r.status_code == 200

#Endpoint de login que simula una autenticacion exitosa, lo que hace que el endpoint responda con un token de acceso
def test_endpoint_login(api):
    with patch("app.routes.auth.cognito_client") as mock:
        mock.authenticate_user.return_value = {
            "success": True, "access_token": "tok", "id_token": "id", "refresh_token": "ref"
        }
        r = api.post("/auth/login", json={"email": "a@b.com", "password": "Pass1!"})
    assert r.status_code == 200
    assert "access_token" in r.json()

# Simula una autenticacion fallida por contraseña incorrecta, lo que hace que el endpoint responda con un error 401 indicando que las credenciales son inválidas
def test_endpoint_login_falla(api):
    with patch("app.routes.auth.cognito_client") as mock:
        mock.authenticate_user.return_value = {"success": False, "error": "Credenciales inválidas"}
        r = api.post("/auth/login", json={"email": "a@b.com", "password": "wrong"})
    assert r.status_code == 401

# Simula el caso de refresco de token exitoso, lo que hace que el endpoint responda con un nuevo token de acceso
def test_endpoint_refresh(api):
    with patch("app.routes.auth.cognito_client") as mock, \
         patch("app.routes.auth.get_secret_hash", return_value="hash"):
        mock.client.admin_get_user.return_value = {"Username": "uuid-123"}
        mock.client.admin_initiate_auth.return_value = {
            "AuthenticationResult": {"AccessToken": "new-tok", "IdToken": "new-id", "RefreshToken": None}
        }
        r = api.post("/auth/refresh", json={"refresh_token": "ref-tok", "email": "a@b.com"})
    assert r.status_code == 200
    assert r.json()["access_token"] == "new-tok"