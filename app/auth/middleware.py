from fastapi import Request, HTTPException
import jwt
from app.auth.cognito import CognitoClient
from app.config import settings

cognito_client = CognitoClient()

# Middleware para verificar JWT en cada solicitud

async def verify_jwt(request: Request):
    
    # Extrae el token del header Authorization
    auth_header = request.headers.get("Authorization")
    
    if not auth_header:
        raise HTTPException(status_code=401, detail="No token provided")
    
    try:
        # Formato: "Bearer <token>"
        scheme, token = auth_header.split()
        
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid scheme")
        
        # Valida el token con Cognito
        result = cognito_client.verify_token(token)
        
        if not result["success"]:
            raise HTTPException(status_code=401, detail=result["error"])
        
        # Devuelve la info del usuario
        return result["payload"]
    
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token format")
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))