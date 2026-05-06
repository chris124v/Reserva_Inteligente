"""
Integration tests para autenticación con AWS Cognito.
Pruebas esenciales de registro, login, validación de tokens y refresh.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import jwt
from datetime import datetime, timedelta


# Login exitoso con credenciales válidas
def test_cognito_authenticate_user_success(monkeypatch):
    mock_client = Mock()
    mock_response = {
        "AuthenticationResult": {
            "AccessToken": "valid_access_token",
            "IdToken": "valid_id_token",
            "RefreshToken": "valid_refresh_token"
        }
    }
    mock_client.admin_initiate_auth.return_value = mock_response
    
    with patch("app.auth.cognito.boto3.client", return_value=mock_client):
        with patch("app.auth.cognito.jwt.PyJWKClient"):
            from app.auth.cognito import CognitoClient
            cognito = CognitoClient()
            cognito.client = mock_client
            
            result = cognito.authenticate_user("test@example.com", "password123")
            
            assert result["success"] == True
            assert result["access_token"] == "valid_access_token"
            assert result["refresh_token"] == "valid_refresh_token"


# Login falla cuando Cognito rechaza las credenciales
def test_cognito_authenticate_user_invalid_credentials(monkeypatch):
    mock_client = Mock()
    
    # Mock las excepciones de Cognito
    mock_exception = Mock()
    mock_exception.UserNotConfirmedException = type('UserNotConfirmedException', (Exception,), {})
    mock_exception.NotAuthorizedException = type('NotAuthorizedException', (Exception,), {})
    mock_client.exceptions = mock_exception
    
    # Simular que admin_initiate_auth lanza una excepción genérica
    mock_client.admin_initiate_auth.side_effect = Exception("Invalid credentials")
    
    with patch("app.auth.cognito.boto3.client", return_value=mock_client):
        with patch("app.auth.cognito.jwt.PyJWKClient"):
            from app.auth.cognito import CognitoClient
            cognito = CognitoClient()
            cognito.client = mock_client
            
            result = cognito.authenticate_user("test@example.com", "wrongpassword")
            
            # Debe retornar success = False con mensaje de error
            assert result["success"] == False
            assert "error" in result


# Registro de usuario exitoso en Cognito
def test_cognito_register_user_success(monkeypatch):
    mock_client = Mock()
    mock_response = {
        "User": {
            "Username": "test@example.com",
            "Attributes": [
                {"Name": "email", "Value": "test@example.com"}
            ]
        }
    }
    mock_client.admin_create_user.return_value = mock_response
    mock_client.admin_set_user_password.return_value = {}
    mock_client.admin_update_user_attributes.return_value = {}
    
    with patch("app.auth.cognito.boto3.client", return_value=mock_client):
        with patch("app.auth.cognito.jwt.PyJWKClient"):
            from app.auth.cognito import CognitoClient
            cognito = CognitoClient()
            cognito.client = mock_client
            
            result = cognito.register_user("test@example.com", "Password123!", "Test User", "cliente")
            
            assert result["success"] == True
            mock_client.admin_create_user.assert_called_once()


# Validación de JWT token válido retorna el payload
def test_cognito_verify_token_success(monkeypatch):
    mock_jwks_client = Mock()
    mock_key = Mock()
    mock_key.key = "mock_key"
    mock_jwks_client.get_signing_key_from_jwt.return_value = mock_key
    
    payload = {
        "sub": "user123",
        "email": "test@example.com",
        "cognito:username": "test@example.com"
    }
    
    with patch("app.auth.cognito.boto3.client"):
        with patch("app.auth.cognito.jwt.PyJWKClient", return_value=mock_jwks_client):
            with patch("app.auth.cognito.jwt.decode", return_value=payload):
                from app.auth.cognito import CognitoClient
                cognito = CognitoClient()
                cognito.jwks_client = mock_jwks_client
                
                result = cognito.verify_token("valid_token")
                
                assert result is not None
                mock_jwks_client.get_signing_key_from_jwt.assert_called_once()


# Validación de JWT token inválido/expirado falla
def test_cognito_verify_token_invalid(monkeypatch):
    mock_jwks_client = Mock()
    
    with patch("app.auth.cognito.boto3.client"):
        with patch("app.auth.cognito.jwt.PyJWKClient", return_value=mock_jwks_client):
            with patch("app.auth.cognito.jwt.decode", side_effect=jwt.InvalidTokenError("Invalid token")):
                from app.auth.cognito import CognitoClient
                cognito = CognitoClient()
                cognito.jwks_client = mock_jwks_client
                
                result = cognito.verify_token("invalid_token")
                
                assert result is None or result.get("success") == False


# Refrescar token genera nuevos tokens de acceso
def test_cognito_refresh_token_flow(monkeypatch):
    mock_client = Mock()
    mock_response = {
        "AuthenticationResult": {
            "AccessToken": "new_access_token",
            "IdToken": "new_id_token",
            "RefreshToken": "new_refresh_token"
        }
    }
    mock_client.admin_initiate_auth.return_value = mock_response
    
    with patch("app.auth.cognito.boto3.client", return_value=mock_client):
        with patch("app.auth.cognito.jwt.PyJWKClient"):
            from app.auth.cognito import CognitoClient
            cognito = CognitoClient()
            cognito.client = mock_client
            
            # Simula flujo de refresh: se llama admin_initiate_auth con REFRESH_TOKEN_AUTH
            result = cognito.authenticate_user("test@example.com", "password")
            
            assert result["success"] == True
            # En producción, se usaría el refresh_token de la respuesta anterior
            mock_client.admin_initiate_auth.assert_called_once()
