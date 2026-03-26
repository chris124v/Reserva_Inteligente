"""
Tests esenciales para el módulo de autenticacion con AWS Cognito. 
"""
 
import pytest
from unittest.mock import MagicMock, patch
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
 
# FIXTURES
 
@pytest.fixture(autouse=True)
def mock_settings():
    with patch("app.auth.cognito.settings") as m:
        m.AWS_REGION = "us-east-2"
        m.COGNITO_USER_POOL_ID = "us-east-2_72geNIkP2"
        m.COGNITO_CLIENT_ID = "fake-client-id"
        m.COGNITO_CLIENT_SECRET = "fake-client-secret"
        yield m
 
 
@pytest.fixture
def cognito(mock_settings):
    with patch("boto3.client"):
        from app.auth.cognito import CognitoClient
        c = CognitoClient()
        c.client = MagicMock()
        return c
 
 
@pytest.fixture
def api():
    with patch("app.auth.cognito.settings") as m:
        m.AWS_REGION = "us-east-2"
        m.COGNITO_USER_POOL_ID = "us-east-2_72geNIkP2"
        m.COGNITO_CLIENT_ID = "fake-client-id"
        m.COGNITO_CLIENT_SECRET = "fake-client-secret"
        with patch("boto3.client"):
            from app.routes.auth import router
            app = FastAPI()
            app.include_router(router)
            return TestClient(app)
 
 

# get_secret_hash
 
def test_secret_hash_es_deterministico():
    from app.auth.cognito import get_secret_hash
    assert get_secret_hash("a", "b", "c") == get_secret_hash("a", "b", "c")
 
def test_secret_hash_diferente_por_usuario():
    from app.auth.cognito import get_secret_hash
    assert get_secret_hash("user1", "b", "c") != get_secret_hash("user2", "b", "c")
 
 
# register_user
 
def test_register_exitoso(cognito):
    cognito.client.admin_create_user.return_value = {}
    cognito.client.admin_set_user_password.return_value = {}
    cognito.client.admin_update_user_attributes.return_value = {}
 
    result = cognito.register_user("new@test.com", "Pass123!", "Test")
    assert result["success"] is True
 
def test_register_falla_si_usuario_existe(cognito):
    cognito.client.admin_create_user.side_effect = Exception("User already exists")
 
    result = cognito.register_user("exist@test.com", "Pass123!", "Test")
    assert result["success"] is False
    assert "error" in result
 
 
# authenticate_user

 
def test_login_exitoso(cognito):
    cognito.client.admin_initiate_auth.return_value = {
        "AuthenticationResult": {
            "AccessToken": "access-token",
            "IdToken": "id-token",
            "RefreshToken": "refresh-token"
        }
    }
 
    result = cognito.authenticate_user("user@test.com", "Pass123!")
    assert result["success"] is True
    assert result["access_token"] == "access-token"
 
def test_login_password_incorrecta(cognito):
    cognito.client.exceptions.NotAuthorizedException = type("NotAuthorizedException", (Exception,), {})
    cognito.client.exceptions.UserNotConfirmedException = type("UserNotConfirmedException", (Exception,), {})
    cognito.client.admin_initiate_auth.side_effect = cognito.client.exceptions.NotAuthorizedException("bad pass")
 
    result = cognito.authenticate_user("user@test.com", "wrong")
    assert result["success"] is False
 
 
# verify_token
 
def test_verify_token_valido(cognito):
    with patch("app.auth.cognito.jwt.get_unverified_header", return_value={"kid": "k1"}), \
         patch("app.auth.cognito.jwt.decode", return_value={"sub": "123", "email": "u@test.com"}):
        cognito.client.get_signing_certificate.return_value = {"Certificate": "fake-cert"}
        result = cognito.verify_token("valid.token")
    assert result["success"] is True
 
def test_verify_token_expirado(cognito):
    import jwt as pyjwt
    with patch("app.auth.cognito.jwt.get_unverified_header", return_value={"kid": "k1"}), \
         patch("app.auth.cognito.jwt.decode", side_effect=pyjwt.ExpiredSignatureError()):
        cognito.client.get_signing_certificate.return_value = {"Certificate": "fake-cert"}
        result = cognito.verify_token("expired.token")
    assert result["success"] is False
    assert "expirado" in result["error"]
 
 
# Middleware
 
@pytest.mark.asyncio
async def test_middleware_sin_token():
    from app.auth.middleware import verify_jwt
    req = MagicMock()
    req.headers.get.return_value = None
    with pytest.raises(HTTPException) as exc:
        await verify_jwt(req)
    assert exc.value.status_code == 401
 
@pytest.mark.asyncio
async def test_middleware_token_valido():
    from app.auth.middleware import verify_jwt
    req = MagicMock()
    req.headers.get.return_value = "Bearer valid.token"
    with patch("app.auth.middleware.cognito_client") as mock:
        mock.verify_token.return_value = {"success": True, "payload": {"sub": "123"}}
        result = await verify_jwt(req)
    assert result["sub"] == "123"
 
 
# Endpoints
 
def test_endpoint_register(api):
    with patch("app.routes.auth.cognito_client") as mock:
        mock.register_user.return_value = {"success": True, "message": "Registrado"}
        r = api.post("/auth/register", json={"email": "a@b.com", "password": "Pass1!", "nombre": "A"})
    assert r.status_code == 200
 
def test_endpoint_login(api):
    with patch("app.routes.auth.cognito_client") as mock:
        mock.authenticate_user.return_value = {
            "success": True, "access_token": "tok", "id_token": "id", "refresh_token": "ref"
        }
        r = api.post("/auth/login", json={"email": "a@b.com", "password": "Pass1!"})
    assert r.status_code == 200
    assert "access_token" in r.json()
 
def test_endpoint_login_falla(api):
    with patch("app.routes.auth.cognito_client") as mock:
        mock.authenticate_user.return_value = {"success": False, "error": "Credenciales inválidas"}
        r = api.post("/auth/login", json={"email": "a@b.com", "password": "wrong"})
    assert r.status_code == 401
 
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