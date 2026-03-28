from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.auth.cognito import CognitoClient

cognito_client = CognitoClient()
security = HTTPBearer(auto_error=False)

# Middleware para verificar JWT en cada solicitud

async def verify_jwt(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    if not credentials:
        raise HTTPException(status_code=401, detail="No token provided")
    
    try:
        if credentials.scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid scheme")

        token = credentials.credentials
        
        # Valida el token con Cognito
        result = cognito_client.verify_token(token)
        
        if not result["success"]:
            raise HTTPException(status_code=401, detail=result["error"])
        
        # Devuelve la info del usuario
        return result["payload"]

    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))