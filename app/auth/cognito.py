import email
import hmac
import hashlib
import base64 # Para generar el secret hash requerido por Cognito
import boto3 #SDK de AWS para comunicarse con cognito
import json

import jwt
from app.config import settings

# Funcion para generar el secret hash requerido por Cognito
def get_secret_hash(username, client_id, client_secret):
    message = bytes(username + client_id, 'utf-8')
    secret = bytes(client_secret, 'utf-8')
    dig = hmac.new(secret, msg=message, digestmod=hashlib.sha256).digest()
    return base64.b64encode(dig).decode()

class CognitoClient:
    def __init__(self):

        # Inicializa el cliente de AWS Cognito
        # Usa boto3 y las credenciales del .env verifica que esten todas
        missing = []
        if not settings.AWS_REGION:
            missing.append("AWS_REGION o AWS_COGNITO_REGION")
        if not settings.COGNITO_USER_POOL_ID:
            missing.append("COGNITO_USER_POOL_ID o AWS_COGNITO_USER_POOL_ID")
        if not settings.COGNITO_CLIENT_ID:
            missing.append("COGNITO_CLIENT_ID o AWS_COGNITO_CLIENT_ID")

        if missing:
            raise ValueError(
                "Faltan variables de entorno de Cognito: " + ", ".join(missing)
            )

        self.client = boto3.client('cognito-idp', region_name=settings.AWS_REGION)
        self.issuer = (
            f"https://cognito-idp.{settings.AWS_REGION}.amazonaws.com/"
            f"{settings.COGNITO_USER_POOL_ID}"
        )
        self.jwks_client = jwt.PyJWKClient(
            f"{self.issuer}/.well-known/jwks.json"
        )
    
    def register_user(self, email: str, password: str, nombre: str, rol: str | None = None):
        
        # Registra un usuario nuevo en Cognito

        try:
            response = self.client.admin_create_user(
                UserPoolId=settings.COGNITO_USER_POOL_ID,
                Username=email,
                TemporaryPassword=password,
                MessageAction='SUPPRESS'  # No envia email automático
    
            )
    
            # Guarda el password permanente
            self.client.admin_set_user_password(
                UserPoolId=settings.COGNITO_USER_POOL_ID,
                Username=email,
                Password=password,
                Permanent=True,
            )

            self.client.admin_update_user_attributes(
                UserPoolId=settings.COGNITO_USER_POOL_ID,
                Username=email,
                UserAttributes=[
                    {'Name': 'email_verified', 'Value': 'true'},
                    {'Name': 'name', 'Value': nombre}
                ]
            )

            #  persistir rol en Cognito como atributo custom.
            
            if rol:
                try:
                    self.client.admin_update_user_attributes(
                        UserPoolId=settings.COGNITO_USER_POOL_ID,
                        Username=email,
                        UserAttributes=[{'Name': 'custom:rol', 'Value': str(rol)}],
                    )
                except Exception:
                    # No fallamos el registro si el atributo no existe/configurada.
                    pass
    
            return {"success": True, "message": "Usuario registrado"}

        except Exception as e:
            return {"success": False, "error": str(e)}
        
        
    
    def authenticate_user(self, email: str, password: str):
        # Autentica y devuelve el JWT

        #Generamos el secret hash
        secret_hash = get_secret_hash(
            email, 
            settings.COGNITO_CLIENT_ID,
            settings.COGNITO_CLIENT_SECRET
        )  

        try:
            response = self.client.admin_initiate_auth(
                UserPoolId=settings.COGNITO_USER_POOL_ID,
                ClientId=settings.COGNITO_CLIENT_ID,
                AuthFlow='ADMIN_NO_SRP_AUTH',
                AuthParameters={
                    'USERNAME': email,
                    'PASSWORD': password,
                    'SECRET_HASH': secret_hash

                }
            )
    
            # Extrae los tokens
            tokens = response['AuthenticationResult']
    
            return {
                "success": True,
                "access_token": tokens['AccessToken'], #Para recursos protegidos
                "id_token": tokens['IdToken'], #Config del usuario
                "refresh_token": tokens.get('RefreshToken') #Para renovar tokens
            }

        #Diversas excepciones comunes de autenticación
        except self.client.exceptions.UserNotConfirmedException:
            return {"success": False, "error": "Usuario no confirmado"}
        except self.client.exceptions.NotAuthorizedException:
            return {"success": False, "error": "Email o contraseña incorrecta"}
        except Exception as e:
            return {"success": False, "error": str(e)}

        
    
    def verify_token(self, token: str):
        # Valida que el token sea legítimo
        
        try:
            # Obtiene la llave pública correcta desde JWKS de Cognito
            signing_key = self.jwks_client.get_signing_key_from_jwt(token).key

            # Verifica firma e issuer
            payload = jwt.decode(
                token,
                signing_key,
                algorithms=['RS256'],
                issuer=self.issuer,
                options={"verify_aud": False}
            )

            # Validacion explícita para access token de este app client
            token_use = payload.get("token_use")
            if token_use != "access":
                return {"success": False, "error": "Token no es access token"}

            client_id = payload.get("client_id") or payload.get("aud")
            if client_id != settings.COGNITO_CLIENT_ID:
                return {"success": False, "error": "Token no pertenece a este cliente"}
    
            return {"success": True, "payload": payload}

        except jwt.ExpiredSignatureError:
            return {"success": False, "error": "Token expirado"}
        except jwt.InvalidIssuerError:
            return {"success": False, "error": "Issuer de token invalido"}
        except jwt.InvalidTokenError:
            return {"success": False, "error": "Token inválido"}
        except Exception as e:
            return {"success": False, "error": str(e)}


    #Busca el ussername real de cognito por atributo de email
    def _find_username_by_email(self, email_value: str) -> str:
        
        response = self.client.list_users(
            UserPoolId=settings.COGNITO_USER_POOL_ID,
            Filter=f'email = "{email_value}"',
            Limit=2,
        )

        #Excepciones en caso de que no se encuentre nada
        users = response.get("Users", [])
        if not users:
            raise ValueError("Usuario no encontrado en Cognito")
        if len(users) > 1:
            raise ValueError("Email duplicado en Cognito")

        username = users[0].get("Username")
        if not username:
            raise ValueError("Respuesta inválida de Cognito (Username faltante)")
        return username

    #Actualiza el email de un usuario dado su emial actual
    def update_user_email(self, current_email: str, new_email: str):
    
        username = self._find_username_by_email(current_email)
        self.client.admin_update_user_attributes(
            UserPoolId=settings.COGNITO_USER_POOL_ID,
            Username=username,
            UserAttributes=[
                {"Name": "email", "Value": new_email},
                {"Name": "email_verified", "Value": "true"},
            ],
        )

    #Obtiene el sub (UUID) de Cognito para un usuario por su email, necesario para sincronizar con BD local
    def get_user_sub_by_email(self, email_value: str) -> str:
        
        response = self.client.list_users(
            UserPoolId=settings.COGNITO_USER_POOL_ID,
            Filter=f'email = "{email_value}"',
            Limit=2,
        )
        users = response.get("Users", [])
        if not users:
            raise ValueError("Usuario no encontrado en Cognito")
        if len(users) > 1:
            raise ValueError("Email duplicado en Cognito")

        attrs = users[0].get("Attributes", [])
        for attr in attrs:
            if attr.get("Name") == "sub":
                value = attr.get("Value")
                if value:
                    return value

        raise ValueError("No se encontró atributo sub en Cognito")